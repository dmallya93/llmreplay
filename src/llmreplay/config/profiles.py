"""llmreplay.yaml profile configuration (Pydantic)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

IgnoreDrift = Literal["warn", "fail"]
STRICT_PROFILES = frozenset({"ci", "strict"})


class ProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ignore_drift: IgnoreDrift = "warn"
    unknown_tool_policy: Literal["static", "fail", "prompt_user"] | None = None
    ignore: list[str] = Field(default_factory=list)
    scrub: list[str] = Field(default_factory=list)
    sticky_writeback: bool = False


class DefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ignore: list[str] = Field(
        default_factory=lambda: [
            "usage",
            "latency_ms",
            "x-request-id",
            "date",
        ]
    )
    scrub: list[str] = Field(default_factory=list)


class LLMReplayFileConfig(BaseModel):
    """Root llmreplay.yaml document."""

    model_config = ConfigDict(extra="allow")

    version: int = 1
    unknown_tool_policy: Literal["static", "fail", "prompt_user"] = "fail"
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    profiles: dict[str, ProfileConfig] = Field(
        default_factory=lambda: {
            "local": ProfileConfig(ignore_drift="warn"),
            "ci": ProfileConfig(ignore_drift="fail", sticky_writeback=False),
            "strict": ProfileConfig(ignore_drift="fail", sticky_writeback=False),
            "debug_sticky": ProfileConfig(ignore_drift="warn", sticky_writeback=True),
        }
    )
    tools: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def resolved_profile(self, name: str) -> ProfileConfig:
        if name not in self.profiles:
            raise KeyError(f"unknown profile: {name}")
        profile = self.profiles[name]
        if name in STRICT_PROFILES and profile.sticky_writeback:
            raise ValueError(f"sticky_writeback must be false for profile {name}")
        return profile

    def fail_on_residual_secrets(self, profile_name: str) -> bool:
        """ci/strict MUST fail record when residual secrets remain (SPEC S2)."""
        return profile_name in STRICT_PROFILES

    def merged_ignore(self, profile_name: str) -> list[str]:
        profile = self.resolved_profile(profile_name)
        seen: set[str] = set()
        out: list[str] = []
        for item in [*self.defaults.ignore, *profile.ignore]:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def merged_scrub_paths(self, profile_name: str) -> list[str]:
        profile = self.resolved_profile(profile_name)
        seen: set[str] = set()
        out: list[str] = []
        for item in [*self.defaults.scrub, *profile.scrub]:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def live_tools(self) -> frozenset[str]:
        """Tool names marked ``class: live`` via ``mark-live`` / yaml."""
        names: set[str] = set()
        for name, entry in self.tools.items():
            if isinstance(entry, dict) and entry.get("class") == "live":
                names.add(str(name))
        return frozenset(names)

    def is_live_tool(self, tool_name: str | None) -> bool:
        if not tool_name:
            return False
        return tool_name in self.live_tools()

    def is_llm_live(self) -> bool:
        """True when LLM proxy calls must hit upstream even in replay."""
        return self.is_live_tool("__llm__") or self.is_live_tool("llm")


def load_llmreplay_yaml(path: Path | None = None) -> LLMReplayFileConfig:
    if path is None or not path.is_file():
        return LLMReplayFileConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return LLMReplayFileConfig.model_validate(data)
