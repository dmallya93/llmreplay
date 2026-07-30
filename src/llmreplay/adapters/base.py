"""ProtocolAdapter protocol — normalize, sort, and SSE per agent wire format."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolAdapter(Protocol):
    """Adapter interface for agent-specific LLM API protocols."""

    @property
    def id(self) -> str:
        """Short stable identifier written into cassette metadata."""
        ...

    def sort_tools_in_messages(self, messages: list[Any]) -> list[Any]:
        """Sort parallel tool blocks so match key is order-insensitive."""
        ...

    def synthesize_sse(self, message: dict[str, Any]) -> bytes:
        """Build a minimal valid SSE body from a stored final JSON message."""
        ...
