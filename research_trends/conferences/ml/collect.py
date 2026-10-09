#!/usr/bin/env python3
"""Cache official ICML/ICLR/NeurIPS proceedings or main-program metadata."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw"
PMLR = {2020: 119, 2021: 139, 2022: 162, 2023: 202, 2024: 235, 2025: 267, 2026: 306}


def sources():
    for year, volume in PMLR.items():
        yield f"icml_{year}.html", f"https://proceedings.mlr.press/v{volume}/"
    for year in range(2020, 2026):
        suffix = "/vol38-main-conference" if year == 2025 else ""
        yield f"neurips_{year}.html", f"https://papers.nips.cc/paper_files/paper/{year}{suffix}"
    yield "iclr_2020.json", "https://iclr.cc/virtual_2020/papers.json"
    for year in range(2021, 2027):
        yield f"iclr_{year}.json", f"https://iclr.cc/static/virtual/data/iclr-{year}-orals-posters.json"
    for year in (2024, 2025, 2026):
        yield f"icml_{year}_program.json", f"https://icml.cc/static/virtual/data/icml-{year}-orals-posters.json"
    yield "neurips_2026_program.json", "https://neurips.cc/static/virtual/data/neurips-2026-orals-posters.json"


def fetch(item):
    name, url = item
    path = RAW / name
    manifest = RAW / (name + ".manifest.json")
    if path.exists() and manifest.exists():
        record = json.loads(manifest.read_text(encoding="utf-8"))
        if record.get("sha256") == hashlib.sha256(path.read_bytes()).hexdigest():
            return {**record, "cache_hit": True}
        raise ValueError(f"cache hash mismatch: {path}")
    record = {"filename": name, "source_url": url, "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AgentEvolutionResearch/0.1 (public metadata)"})
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read(25_000_001)
            record.update({"http_status": response.status, "final_url": response.url})
        if len(raw) > 25_000_000:
            raise ValueError("source file exceeds 25 MB local cap")
        path.write_bytes(raw)
        record.update({"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    except Exception as exc:
        record["error"] = repr(exc)
    manifest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, sources()))
    for record in records:
        print(json.dumps(record, ensure_ascii=False))
    if any("error" in record for record in records):
        raise SystemExit("some public source files are missing; inspect manifests and retry")
