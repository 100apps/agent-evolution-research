#!/usr/bin/env python3
"""Annual, same-source review-type sensitivity for 2020 and 2025 endpoints."""

from __future__ import annotations

import csv
import json
import urllib.parse
from pathlib import Path

from collect_openalex import BASE, TYPE_FILTER, fetch, sha256


def query(year, ai):
    filters = ",".join((f"from_publication_date:{year}-01-01",
                        f"to_publication_date:{year}-12-31",
                        f"type:{TYPE_FILTER}", "is_retracted:false"))
    if ai:
        filters += ",primary_topic.subfield.id:1702"
    return BASE + "?" + urllib.parse.urlencode(
        {"filter": filters, "group_by": "type", "per_page": 100})


def run(data_dir):
    rows = []
    for year in (2020, 2025):
        for ai in (False, True):
            url = query(year, ai)
            obj, raw_hash = fetch(url, data_dir / "raw/openalex", data_dir / "query_audit.jsonl", 800)
            groups = obj.get("group_by") if obj else None
            if not isinstance(groups, list) or sum(group["count"] for group in groups) != obj["meta"]["count"]:
                rows.append({"year": year, "scope": "AI_1702" if ai else "global", "type": "",
                             "count": "", "status": "missing", "query_sha256": sha256(url.encode()),
                             "raw_sha256": raw_hash or ""})
                continue
            for group in groups:
                rows.append({"year": year, "scope": "AI_1702" if ai else "global",
                             "type": group["key"], "count": group["count"], "status": "ok",
                             "query_sha256": sha256(url.encode()), "raw_sha256": raw_hash})
    path = data_dir / "openalex_annual_type_sensitivity.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"rows": len(rows), "ok": sum(row["status"] == "ok" for row in rows)},
                     ensure_ascii=False))


if __name__ == "__main__":
    run(Path("research_trends/data"))
