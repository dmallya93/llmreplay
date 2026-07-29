"""Diagnostic bundle export (`llmreplay bundle`)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from llmreplay.diagnose.validate import validate_cassette
from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore


class BundleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    files: int
    scrubbed: bool


def create_bundle(
    cassette_dir: Path,
    output: Path,
    *,
    scrub: bool = True,
    include_bodies: bool = False,
) -> BundleResult:
    """Write a previewable zip. Secrets scrubbed by default (SPEC / DESIGN)."""
    store = CassetteStore(cassette_dir)
    scrubber = Scrubber()
    report = validate_cassette(cassette_dir, scan_secrets=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "validate.json",
            json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        )
        count += 1
        if store.manifest_path.is_file():
            zf.write(store.manifest_path, arcname="cassette.json")
            count += 1
        for sub in ("requests", "responses"):
            folder = store.root / sub
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.json")):
                text = path.read_text(encoding="utf-8")
                if scrub:
                    try:
                        data = json.loads(text)
                        text = (
                            json.dumps(scrubber.scrub_value(data), indent=2, sort_keys=True) + "\n"
                        )
                    except json.JSONDecodeError:
                        text = scrubber.scrub_raw_text(text)
                zf.writestr(f"{sub}/{path.name}", text)
                count += 1
        if include_bodies:
            bodies = store.root / "bodies"
            if bodies.is_dir():
                for path in sorted(bodies.iterdir()):
                    if path.is_file():
                        zf.write(path, arcname=f"bodies/{path.name}")
                        count += 1
        zf.writestr(
            "README.txt",
            "LLMReplay diagnostic bundle. Scrubbed by default; bodies omitted unless opted in.\n",
        )
        count += 1
    return BundleResult(path=str(output), files=count, scrubbed=scrub)
