"""Structural tests for the Claude Code plugin — valid JSON, skill files exist."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugins" / "llmreplay"


@pytest.mark.unit
def test_plugin_json_is_valid() -> None:
    plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    assert plugin_json.is_file(), f"{plugin_json} does not exist"
    data = json.loads(plugin_json.read_text())
    assert "name" in data
    assert "skills" in data
    assert isinstance(data["skills"], list)
    assert len(data["skills"]) >= 1


@pytest.mark.unit
def test_skill_files_exist() -> None:
    plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text())
    for skill_path in data["skills"]:
        full = PLUGIN_ROOT / skill_path
        assert full.is_file(), f"skill file {full} does not exist"


@pytest.mark.unit
def test_skills_have_frontmatter() -> None:
    plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text())
    for skill_path in data["skills"]:
        full = PLUGIN_ROOT / skill_path
        content = full.read_text()
        assert content.startswith("---"), f"{skill_path} missing YAML frontmatter"
        end = content.index("---", 3)
        frontmatter = content[3:end]
        assert "description:" in frontmatter, f"{skill_path} missing description"
