#!/usr/bin/env python3
"""Reproducible small metadata sample for qualitative, source-separated review."""

from __future__ import annotations

import csv
import json
import urllib.parse
from pathlib import Path

from collect_openalex import BASE, TYPE_FILTER, fetch, month_dates, sha256

MONTHS = ("2020-09", "2023-09", "2025-09")
STRATA = {"cs_primary": "primary_topic.field.id:17",
          "ai_primary": "primary_topic.subfield.id:1702",
          "marketing_primary": "primary_topic.subfield.id:1406"}
SAMPLE_N = 20
SEED = 20261009


def sample_url(month: str, stratum: str) -> str:
    start, end = month_dates(month)
    filters = ",".join((f"from_publication_date:{start}", f"to_publication_date:{end}",
                        f"type:{TYPE_FILTER}", "is_retracted:false", STRATA[stratum]))
    params = {"filter": filters, "sample": SAMPLE_N, "seed": SEED, "per_page": SAMPLE_N,
              "select": "id,title,publication_date,primary_topic,topics,abstract_inverted_index,type,doi"}
    return BASE + "?" + urllib.parse.urlencode(params)


def abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    length = max((position for positions in inverted.values() for position in positions), default=-1) + 1
    words = [""] * length
    for word, positions in inverted.items():
        for position in positions:
            words[position] = word
    return " ".join(words)


def run(data_dir: Path):
    rows = []
    for month in MONTHS:
        for stratum in STRATA:
            url = sample_url(month, stratum)
            obj, raw_hash = fetch(url, data_dir / "raw" / "openalex", data_dir / "query_audit.jsonl", 800)
            if obj is None:
                rows.append({"month": month, "stratum": stratum, "sample_seed": SEED, "requested_n": SAMPLE_N,
                             "status": "missing", "query_sha256": sha256(url.encode()), "raw_sha256": raw_hash or ""})
                continue
            results = obj.get("results")
            if not isinstance(results, list) or len(results) != SAMPLE_N:
                raise ValueError(f"unexpected sample response {month} {stratum}: {len(results) if isinstance(results,list) else type(results)}")
            for work in results:
                topic = work.get("primary_topic") or {}
                rows.append({"month": month, "stratum": stratum, "sample_seed": SEED, "requested_n": SAMPLE_N,
                             "status": "ok", "work_id": work.get("id"), "title": work.get("title"),
                             "publication_date": work.get("publication_date"), "work_type": work.get("type"),
                             "doi": work.get("doi"), "primary_subfield_id": (topic.get("subfield") or {}).get("id"),
                             "abstract": abstract(work.get("abstract_inverted_index")),
                             "query_sha256": sha256(url.encode()), "raw_sha256": raw_hash})
    path = data_dir / "openalex_metadata_sample.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"sample_rows": len(rows), "ok": sum(row["status"] == "ok" for row in rows),
                      "csv": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    run(Path("research_trends/data"))
