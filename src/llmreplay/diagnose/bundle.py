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
            text = store.manifest_path.read_text(encoding="utf-8")
            if scrub:
                try:
                    data = json.loads(text)
                    text = json.dumps(scrubber.scrub_value(data), indent=2, sort_keys=True) + "\n"
                except json.JSONDecodeError:
                    text = scrubber.scrub_raw_text(text)
            zf.writestr("cassette.json", text)
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
                    if not path.is_file():
                        continue
                    raw = path.read_bytes()
                    if scrub:
                        try:
                            text = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            text = raw.decode("utf-8", errors="replace")
                        raw = scrubber.scrub_raw_text(text).encode("utf-8")
                    zf.writestr(f"bodies/{path.name}", raw)
                    count += 1
        note = (
            "LLMReplay diagnostic bundle. Scrubbed by default; "
            "bodies omitted unless --include-bodies (still scrubbed when scrub=True).\n"
        )
        zf.writestr("README.txt", note)
        count += 1
    return BundleResult(path=str(output), files=count, scrubbed=scrub)
