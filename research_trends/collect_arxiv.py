#!/usr/bin/env python3
"""Serial, cached arXiv Atom count collector with first-submission month filters."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://export.arxiv.org/api/query"
SCOPE_VERSION = "arxiv-core5-v1.0.2"
MIN_INTERVAL_SECONDS = 3.5
QUERIES = {
    "all_arxiv": "",
    "cs_plus_stat_ml": "(cat:cs.* OR cat:stat.ML)",
    "core_ai_5_category_proxy": "(cat:cs.AI OR cat:cs.LG OR cat:stat.ML OR cat:cs.CL OR cat:cs.CV)",
    "core_ai_5_in_cs": "(cat:cs.AI OR cat:cs.LG OR cat:stat.ML OR cat:cs.CL OR cat:cs.CV) AND cat:cs.*",
    "cs_only": "cat:cs.*",
}
INTERNAL_TAXONOMY_PATH = Path(__file__).parent / "methodology" / "arxiv_strict_queries.json"
INTERNAL_PILOT_MONTHS = ("2023-01", "2024-01", "2026-09")
PILOT_MONTHS = ("2020-09", "2023-09", "2026-09")
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}totalResults"


def months():
    year, number = 2020, 1
    while (year, number) <= (2026, 9):
        yield f"{year:04d}-{number:02d}"
        number += 1
        if number == 13:
            year, number = year + 1, 1


def query(month: str, metric: str) -> str:
    year, number = map(int, month.split("-"))
    start = f"{year:04d}{number:02d}010000"
    end = f"{year:04d}{number:02d}{calendar.monthrange(year, number)[1]:02d}2359"
    date = f"submittedDate:[{start} TO {end}]"
    if metric in QUERIES:
        scope = QUERIES[metric]
        search = f"{scope} AND {date}" if scope else date
    else:
        internal = json.loads(INTERNAL_TAXONOMY_PATH.read_text(encoding="utf-8"))
        scope = internal["scope"]
        category = internal["queries"][metric]
        search = f"({scope}) AND ({category}) AND {date}"
    return BASE + "?" + urllib.parse.urlencode({"search_query": search, "start": 0, "max_results": 1})


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append_audit(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def attempt_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(json.loads(line).get("event") == "http_attempt" for line in path.open(encoding="utf-8"))


def rate_wait(path: Path):
    if not path.exists():
        return
    records = [json.loads(line) for line in path.open(encoding="utf-8")]
    times = [datetime.fromisoformat(x["at_utc"]) for x in records if x.get("event") == "http_attempt"]
    if times:
        remaining = MIN_INTERVAL_SECONDS - (datetime.now(timezone.utc) - times[-1]).total_seconds()
        if remaining > 0:
            time.sleep(remaining)


def parse_count(raw: bytes) -> int:
    root = ET.fromstring(raw)
    node = root.find(OPENSEARCH)
    if node is None or node.text is None:
        raise ValueError("missing opensearch totalResults")
    value = int(node.text)
    if value < 0:
        raise ValueError("negative totalResults")
    return value


def fetch(url: str, raw_dir: Path, audit_path: Path, max_calls: int):
    key = sha256(url.encode())
    path = raw_dir / f"{key}.xml"
    if path.exists():
        raw = path.read_bytes()
        try:
            count = parse_count(raw)
            append_audit(audit_path, {"event": "cache_hit", "url": url, "query_sha256": key,
                                      "raw_sha256": sha256(raw)})
            return count, sha256(raw)
        except (ValueError, ET.ParseError) as exc:
            append_audit(audit_path, {"event": "cache_invalid", "url": url, "error": repr(exc)})
            return None, None
    for attempt in range(1, 4):
        if attempt_count(audit_path) >= max_calls:
            append_audit(audit_path, {"event": "budget_stop", "url": url, "query_sha256": key})
            return None, None
        rate_wait(audit_path)
        stamp = datetime.now(timezone.utc).isoformat()
        event = {"event": "http_attempt", "at_utc": stamp, "url": url,
                 "query_sha256": key, "attempt": attempt}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agent-evolution-research-trends/0.1", "Accept": "application/atom+xml"})
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read(2_000_001)
                event["http_status"] = response.status
                event["content_type"] = response.headers.get("Content-Type")
            if len(raw) > 2_000_000:
                raise ValueError("response unexpectedly large")
            count = parse_count(raw)
            raw_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            event.update({"raw_sha256": sha256(raw), "total_results": count})
            append_audit(audit_path, event)
            return count, sha256(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read(5000)
            event.update({"http_status": exc.code, "error": str(exc), "error_body_sha256": sha256(body),
                          "error_body_excerpt": body.decode("utf-8", errors="replace")[:500]})
            append_audit(audit_path, event)
            if exc.code not in (500, 502, 503, 504) or attempt == 3:
                return None, None
        except (urllib.error.URLError, TimeoutError, ValueError, ET.ParseError) as exc:
            event["error"] = repr(exc)
            append_audit(audit_path, event)
            if attempt == 3:
                return None, None
        time.sleep(2 ** attempt)
    return None, None


def run(output_dir: Path, scope: str, max_calls: int):
    audit = output_dir / "arxiv_query_audit.jsonl"
    raw_dir = output_dir / "raw" / "arxiv"
    internal_mode = scope.startswith("internal")
    selected = (list(INTERNAL_PILOT_MONTHS if scope == "internal-pilot" else
                     (m for m in months() if m >= "2023-01")) if internal_mode else
                list(PILOT_MONTHS if scope == "pilot" else months()))
    metrics = (tuple(json.loads(INTERNAL_TAXONOMY_PATH.read_text(encoding="utf-8"))["queries"])
               if internal_mode else
               ("all_arxiv", "cs_plus_stat_ml", "core_ai_5_category_proxy", "core_ai_5_in_cs", "cs_only")
               if scope == "pilot" else ("all_arxiv", "cs_plus_stat_ml", "core_ai_5_category_proxy"))
    rows = []
    for month in selected:
        counts = {}
        for metric in metrics:
            url = query(month, metric)
            count, raw_hash = fetch(url, raw_dir, audit, max_calls)
            counts[metric] = count
            rows.append({"month": month, "metric": metric, "count": count, "status": "ok" if count is not None else "missing",
                         "query_sha256": sha256(url.encode()), "raw_sha256": raw_hash or "",
                         "scope_version": SCOPE_VERSION, "date_semantics": "submittedDate UTC"})
        if not internal_mode and all(x is not None for x in counts.values()) and not (
            counts["core_ai_5_category_proxy"] <= counts["cs_plus_stat_ml"] <= counts["all_arxiv"]
            and (scope != "pilot" or (counts["core_ai_5_in_cs"] <= counts["core_ai_5_category_proxy"]
                                       and counts["core_ai_5_in_cs"] <= counts["cs_only"] <= counts["cs_plus_stat_ml"]))):
            raise ValueError(f"non-nested arXiv counts {month}: {counts}")
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = {"pilot": "arxiv_pilot.csv", "full": "arxiv_monthly.csv",
                "internal-pilot": "arxiv_internal_pilot.csv", "internal-full": "arxiv_internal_monthly.csv"}[scope]
    csv_path = output_dir / filename
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"months": len(selected), "rows": len(rows), "ok": sum(r["status"] == "ok" for r in rows),
                      "requests": attempt_count(audit), "csv": str(csv_path)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("research_trends/data"))
    parser.add_argument("--scope", choices=("pilot", "full", "internal-pilot", "internal-full"), default="pilot")
    parser.add_argument("--max-calls", type=int, default=600)
    args = parser.parse_args()
    run(args.output_dir, args.scope, args.max_calls)
