#!/usr/bin/env python3
"""Cache current OpenAlex primary AI-topic group counts by publication month."""

from __future__ import annotations

import csv
import json
import urllib.parse
from pathlib import Path

from collect_openalex import BASE, TYPE_FILTER, fetch, month_dates, months, sha256


def query(month: str) -> str:
    start, end = month_dates(month)
    filters = ",".join((f"from_publication_date:{start}", f"to_publication_date:{end}",
                        f"type:{TYPE_FILTER}", "is_retracted:false",
                        "primary_topic.subfield.id:1702"))
    return BASE + "?" + urllib.parse.urlencode(
        {"filter": filters, "group_by": "primary_topic.id", "per_page": 200})


def run(data_dir: Path, selected: list[str]):
    rows, coverage = [], []
    for month in selected:
        url = query(month)
        obj, raw_hash = fetch(url, data_dir / "raw" / "openalex",
                              data_dir / "query_audit.jsonl", 800)
        query_hash = sha256(url.encode())
        groups = obj.get("group_by") if obj else None
        total = obj["meta"]["count"] if obj else None
        valid = isinstance(groups, list) and not obj["meta"].get("next_cursor") and (
            sum(group.get("count", 0) for group in groups) == total)
        coverage.append({"month": month, "status": "ok" if valid else "missing_or_incomplete_group_page",
                         "ai_primary_total": total if valid else None, "groups": len(groups) if valid else None,
                         "query_sha256": query_hash, "raw_sha256": raw_hash or ""})
        if valid:
            for group in groups:
                rows.append({"month": month, "topic_id": str(group["key"]).rstrip("/").split("/")[-1],
                             "topic_name_current": group.get("key_display_name", ""),
                             "works": group["count"], "ai_primary_total": total,
                             "query_sha256": query_hash, "raw_sha256": raw_hash,
                             "rule_version": "openalex-primary-topic-core-v1"})
    data_dir.mkdir(parents=True, exist_ok=True)
    for path, items in ((data_dir / "openalex_ai_topics.csv", rows),
                        (data_dir / "openalex_ai_topics_coverage.csv", coverage)):
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(items[0]))
            writer.writeheader()
            writer.writerows(items)
    print(json.dumps({"months": len(selected), "ok": sum(row["status"] == "ok" for row in coverage),
                      "topic_rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    run(Path("research_trends/data"), ["2023-01", "2024-01", "2026-09"] if args.pilot
        else list(months("2023-01", "2026-09")))
