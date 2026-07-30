"""Free-key gate for the local proxy (SPEC S8)."""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse

from llmreplay.teststack.keys import FREE_KEY_PREFIX, FreeKeyStore


def extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("x-api-key")
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return auth.strip()


def enforce_free_key(
    request: Request,
    *,
    store_path: Path | None,
    require_free_key: bool = False,
    allow_remote: bool = False,
) -> JSONResponse | None:
    """Validate free keys when presented, or when free_mode requires them.

    Return an error response or None to continue.
    """
    token = extract_bearer_token(request)
    if token is None or not token.startswith(FREE_KEY_PREFIX):
        if require_free_key:
            return JSONResponse(
                {
                    "error": {
                        "type": "llmreplay_free_key",
                        "message": "401 free mode requires llmreplay-free-* Authorization",
                    }
                },
                status_code=401,
            )
        return None
    peer = request.client.host if request.client else ""
    store = FreeKeyStore(store_path or (Path.home() / ".llmreplay" / "free-keys.json"))
    try:
        if not allow_remote:
            store.assert_localhost(peer)
        if store.get(token) is None:
            return JSONResponse(
                {
                    "error": {
                        "type": "llmreplay_free_key",
                        "message": "unknown free key",
                    }
                },
                status_code=401,
            )
        store.consume(token, units=1)
    except PermissionError as exc:
        return JSONResponse(
            {
                "error": {
                    "type": "llmreplay_free_key",
                    "message": str(exc),
                }
            },
            status_code=403,
        )
    except RuntimeError as exc:
        return JSONResponse(
            {
                "error": {
                    "type": "llmreplay_free_key",
                    "message": str(exc),
                }
            },
            status_code=429,
        )
    return None
