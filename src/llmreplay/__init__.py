"""LLMReplay — VCR / time-travel replay for coding agents.

Public API — import from ``llmreplay`` directly::

    from llmreplay import ReplayTransport, RecordTransport, Scrubber
    from llmreplay import create_app, match_key, ProxyConfig
    from llmreplay import CassetteStore, load_llmreplay_yaml

Imports are deferred so that ``pytest-cov`` can start measurement before
the covered modules are loaded (the pytest plugin entry point triggers
``import llmreplay`` during startup, before coverage begins).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "CassetteStore",
    "ProxyConfig",
    "RecordTransport",
    "ReplayTransport",
    "Scrubber",
    "create_app",
    "load_llmreplay_yaml",
    "match_key",
]


def __getattr__(name: str) -> object:
    """Lazy-load public API symbols on first access."""
    if name == "match_key":
        from llmreplay.core.match import match_key  # noqa: PLC0415
        return match_key
    if name == "create_app":
        from llmreplay.proxy.app import create_app  # noqa: PLC0415
        return create_app
    if name == "ProxyConfig":
        from llmreplay.proxy.config import ProxyConfig  # noqa: PLC0415
        return ProxyConfig
    if name == "Scrubber":
        from llmreplay.scrub.engine import Scrubber  # noqa: PLC0415
        return Scrubber
    if name == "CassetteStore":
        from llmreplay.store.cassette import CassetteStore  # noqa: PLC0415
        return CassetteStore
    if name == "load_llmreplay_yaml":
        from llmreplay.config.profiles import load_llmreplay_yaml  # noqa: PLC0415
        return load_llmreplay_yaml
    if name in ("RecordTransport", "ReplayTransport"):
        from llmreplay import transport  # noqa: PLC0415
        return getattr(transport, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from llmreplay.config.profiles import load_llmreplay_yaml
    from llmreplay.core.match import match_key
    from llmreplay.proxy.app import create_app
    from llmreplay.proxy.config import ProxyConfig
    from llmreplay.scrub.engine import Scrubber
    from llmreplay.store.cassette import CassetteStore
    from llmreplay.transport import RecordTransport, ReplayTransport
