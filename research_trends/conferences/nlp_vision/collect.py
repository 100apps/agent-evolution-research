#!/usr/bin/env python3
"""Cache official ACL Anthology XML and CVF main-proceedings indexes."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw"


def sources():
    for year in range(2020, 2027):
        yield f"acl_{year}.xml", f"https://raw.githubusercontent.com/acl-org/acl-anthology/master/data/xml/{year}.acl.xml"
        if year == 2020:
            for day in (16, 17, 18):
                yield f"cvpr_2020_day{day}.html", f"https://openaccess.thecvf.com/CVPR2020.py?day=2020-06-{day}"
        else:
            yield f"cvpr_{year}.html", f"https://openaccess.thecvf.com/CVPR{year}?day=all"


def fetch(item):
    name, url = item
    path = RAW / name
    manifest_path = RAW / (name + ".manifest.json")
    if path.exists() and manifest_path.exists():
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
        if record.get("sha256") == hashlib.sha256(path.read_bytes()).hexdigest():
            return {**record, "cache_hit": True}
        raise ValueError(f"cache hash mismatch: {path}")
    record = {"filename": name, "source_url": url,
              "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
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
    manifest_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, sources()))
    for record in records:
        print(json.dumps(record, ensure_ascii=False))
    if any("error" in record for record in records):
        raise SystemExit("some public source files were missing; inspect manifests and retry")
