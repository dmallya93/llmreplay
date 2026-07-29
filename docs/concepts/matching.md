# Matching

Pipeline (SPEC S1):

1. Strip `ignore` keys
2. Strip thinking/reasoning blocks from the hash projection
3. Sort parallel tool_use / tool_result blocks
4. RFC 8785 JCS canonicalize
5. `SHA-256` → match key (hex)

```python
from llmreplay.core.match import match_key

key = match_key({"model": "x", "messages": [], "usage": {"input_tokens": 1}})
# usage ignored — same key without usage field
```

Never auto-promote: a static miss is exit code `1` (`STATIC_MISMATCH`).
