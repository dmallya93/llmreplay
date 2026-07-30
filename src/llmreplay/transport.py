"""In-process httpx transports for record and replay (no uvicorn needed).

Usage::

    from llmreplay import ReplayTransport
    transport = ReplayTransport(cassette_dir=Path(".llmreplay/cassette"))
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.post("http://llmreplay/v1/messages", json={...})
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.scrub.engine import Scrubber


class ReplayTransport(httpx.ASGITransport):
    """In-process replay transport — no port binding required."""

    def __init__(
        self,
        cassette_dir: Path,
        *,
        profile: str = "ci",
        config_path: Path | None = None,
        scrubber: Scrubber | None = None,
        allow_live: bool = False,
        **kwargs: Any,
    ) -> None:
        config = ProxyConfig(
            mode="replay",
            cassette_dir=cassette_dir,
            profile=profile,
            config_path=config_path,
            allow_live=allow_live,
        )
        app = create_app(config=config, scrubber=scrubber)
        super().__init__(app=app, **kwargs)


class RecordTransport(httpx.ASGITransport):
    """In-process record transport — captures to cassette without a server."""

    def __init__(
        self,
        cassette_dir: Path,
        *,
        upstream_base: str,
        profile: str = "local",
        config_path: Path | None = None,
        scrubber: Scrubber | None = None,
        http_client_factory: Any | None = None,
        **kwargs: Any,
    ) -> None:
        config = ProxyConfig(
            mode="record",
            cassette_dir=cassette_dir,
            upstream_base=upstream_base,
            profile=profile,
            config_path=config_path,
        )
        app = create_app(
            config=config,
            scrubber=scrubber,
            http_client_factory=http_client_factory,
        )
        super().__init__(app=app, **kwargs)
