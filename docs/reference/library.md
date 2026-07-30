# Library API reference

> **Stability:** Alpha (0.x). Public symbols may change with minor bumps until 0.2.

## Public surface

All stable symbols are re-exported from the top-level `llmreplay` package:

```python
from llmreplay import (
    CassetteStore,
    ProxyConfig,
    RecordTransport,
    ReplayTransport,
    Scrubber,
    create_app,
    load_llmreplay_yaml,
    match_key,
)
```

### Transports (no server needed)

`ReplayTransport` and `RecordTransport` wrap `httpx.ASGITransport` around the proxy ASGI app. Use them for in-process record/replay without binding a port:

```python
from pathlib import Path
import httpx
from llmreplay import ReplayTransport

transport = ReplayTransport(cassette_dir=Path(".llmreplay/cassette"))
async with httpx.AsyncClient(transport=transport, base_url="http://llmreplay") as client:
    resp = await client.post("/v1/messages", json={...})
```

#### `ReplayTransport(cassette_dir, *, profile="ci", config_path=None, scrubber=None, allow_live=False)`

Replays from a recorded cassette. Raises `404` on miss (same as the proxy).

#### `RecordTransport(cassette_dir, *, upstream_base, profile="local", config_path=None, scrubber=None, http_client_factory=None)`

Records upstream responses into a cassette directory.

### Core utilities

| Symbol | Purpose |
|---|---|
| `match_key(event, *, ignore_keys, scrubber)` | Compute the SHA-256 static match key for a normalized request event |
| `CassetteStore(path)` | Read/write cassette manifests and transactions |
| `Scrubber(hmac_key=...)` | HMAC-based secret scrubbing engine |
| `create_app(config=...)` | Build the Starlette ASGI proxy app |
| `ProxyConfig(mode=..., cassette_dir=...)` | Validated proxy configuration |
| `load_llmreplay_yaml(path)` | Load and parse `llmreplay.yaml` |

### Parity sessions

Pre-built multi-turn protocol fixtures for testing:

```python
from llmreplay.parity import claude_tool_session, codex_responses_session
from llmreplay.parity.harness import record_session, replay_session
```

See `tests/test_c9_parity.py` for usage patterns.
