"""Protocol adapters — abstract agent-specific normalization, sorting, and SSE."""

from llmreplay.adapters.base import ProtocolAdapter
from llmreplay.adapters.registry import adapter_for_path

__all__ = ["ProtocolAdapter", "adapter_for_path"]
