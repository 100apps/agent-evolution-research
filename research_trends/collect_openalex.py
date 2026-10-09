#!/usr/bin/env python3
"""Cache and audit small OpenAlex monthly-count queries. No credentials required."""

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
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.openalex.org/works"
TYPE_FILTER = "article|preprint|conference-paper|review"
RULE_VERSION = "openalex-primary-topic-core-v1"
PILOT_MONTHS = ("2020-09", "2023-09", "2026-09")
FIRST_MONTH = "2020-01"
LAST_MONTH = "2026-09"
MAX_CALLS = 800
USER_AGENT = "agent-evolution-research-trends/0.1 (public research; anonymous)"


def months(first: str, last: str):
    year, month = map(int, first.split("-"))
    end_year, end_month = map(int, last.split("-"))
    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year, month = year + 1, 1


def month_dates(month: str) -> tuple[str, str]:
    year, number = map(int, month.split("-"))
    return f"{month}-01", f"{month}-{calendar.monthrange(year, number)[1]:02d}"


def query(month: str, metric: str, first_day: bool = False) -> str:
    start, end = month_dates(month)
    if first_day:
        end = start
    parts = [f"from_publication_date:{start}", f"to_publication_date:{end}",
             f"type:{TYPE_FILTER}", "is_retracted:false"]
    if metric == "ai_primary_1702":
        parts.append("primary_topic.subfield.id:1702")
    elif metric == "ai_vision_primary_1702_1707":
        parts.append("primary_topic.subfield.id:1702|1707")
    elif metric == "marketing_primary_1406":
        parts.append("primary_topic.subfield.id:1406")
    elif metric == "marketing_with_ai_vision_cotag":
        parts.extend(("primary_topic.subfield.id:1406", "topics.subfield.id:1702|1707"))
    elif metric != "global_and_fields":
        raise ValueError(metric)
    params = {"filter": ",".join(parts), "per_page": "1", "select": "id"}
    if metric == "global_and_fields":
        params = {"filter": ",".join(parts), "group_by": "primary_topic.field.id:include_unknown", "per_page": "100"}
    return BASE + "?" + urllib.parse.urlencode(params)


def diagnostic_query(month: str, group_by: str) -> str:
    start, end = month_dates(month)
    if group_by == "first_day":
        end = start
    filters = ",".join((f"from_publication_date:{start}", f"to_publication_date:{end}",
                        f"type:{TYPE_FILTER}", "is_retracted:false"))
    params = {"filter": filters, "group_by": group_by, "per_page": "100"}
    if group_by == "first_day":
        params = {"filter": filters, "per_page": "1", "select": "id"}
    return BASE + "?" + urllib.parse.urlencode(params)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append_jsonl(path: Path, item: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def physical_call_count(audit_path: Path) -> int:
    if not audit_path.exists():
        return 0
    with audit_path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if json.loads(line).get("event") == "http_attempt")


def fetch(url: str, raw_dir: Path, audit_path: Path, max_calls: int) -> tuple[dict | None, str | None]:
    key = sha256(url.encode("utf-8"))
    raw_path = raw_dir / f"{key}.json"
    if raw_path.exists():
        raw = raw_path.read_bytes()
        try:
            obj = json.loads(raw)
            append_jsonl(audit_path, {"event": "cache_hit", "at_utc": datetime.now(timezone.utc).isoformat(),
                                     "url": url, "query_sha256": key, "raw_sha256": sha256(raw)})
            return obj, sha256(raw)
        except json.JSONDecodeError:
            append_jsonl(audit_path, {"event": "cache_corrupt", "at_utc": datetime.now(timezone.utc).isoformat(),
                                     "url": url, "query_sha256": key})
            return None, None
    for attempt in range(1, 4):
        if physical_call_count(audit_path) >= max_calls:
            append_jsonl(audit_path, {"event": "budget_stop", "url": url, "query_sha256": key})
            return None, None
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        event = {"event": "http_attempt", "at_utc": datetime.now(timezone.utc).isoformat(),
                 "url": url, "query_sha256": key, "attempt": attempt}
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                event.update({"http_status": response.status, "raw_sha256": sha256(raw),
                              "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
                              "rate_limit_credits_used": response.headers.get("X-RateLimit-Credits-Used")})
            obj = json.loads(raw)
            if not isinstance(obj, dict) or not isinstance(obj.get("meta"), dict) or not isinstance(obj["meta"].get("count"), int):
                event["parse_error"] = "missing integer meta.count"
                append_jsonl(audit_path, event)
                return None, None
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            event["meta_cost"] = obj["meta"].get("cost")
            append_jsonl(audit_path, event)
            time.sleep(1.0)
            return obj, sha256(raw)
        except urllib.error.HTTPError as exc:
            event.update({"http_status": exc.code, "error": str(exc)})
            append_jsonl(audit_path, event)
            if exc.code not in (500, 502, 503, 504) or attempt == 3:
                return None, None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            event["error"] = repr(exc)
            append_jsonl(audit_path, event)
            if attempt == 3:
                return None, None
        time.sleep(2 ** attempt)
    return None, None


def field_is_cs(key: object) -> bool:
    return str(key).rstrip("/").split("/")[-1] == "17"


def field_is_unknown(key: object) -> bool:
    return str(key).rstrip("/").split("/")[-1] == "unknown"


def run(output_dir: Path, selected_months: list[str], max_calls: int, first_day: bool = False,
        metrics: tuple[str, ...] = ("global_and_fields", "ai_primary_1702", "ai_vision_primary_1702_1707"),
        output_name: str | None = None):
    raw_dir = output_dir / "raw" / "openalex"
    audit_path = output_dir / "query_audit.jsonl"
    rows = []
    for month in selected_months:
        for metric in metrics:
            url = query(month, metric, first_day=first_day)
            obj, raw_hash = fetch(url, raw_dir, audit_path, max_calls)
            row = {"month": month, "metric": metric, "status": "missing", "count": "",
                   "query_sha256": sha256(url.encode("utf-8")), "raw_sha256": raw_hash or "",
                   "rule_version": RULE_VERSION, "source": "OpenAlex API default core corpus"}
            if obj is not None:
                row.update({"status": "ok", "count": obj["meta"]["count"]})
                if metric == "global_and_fields":
                    groups = obj.get("group_by")
                    if not isinstance(groups, list) or obj["meta"].get("next_cursor"):
                        row["status"] = "invalid_group_pagination"
                        row["count"] = ""
                    else:
                        cs = [g for g in groups if field_is_cs(g.get("key"))]
                        if len(cs) != 1 or sum(g.get("count", 0) for g in groups) != obj["meta"]["count"]:
                            row["status"] = "invalid_group_total"
                            row["count"] = ""
                        else:
                            row["cs_field_17_count"] = cs[0]["count"]
                            row["unknown_field_count"] = sum(g["count"] for g in groups if field_is_unknown(g.get("key")))
            rows.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / (output_name or ("openalex_first_day.csv" if first_day else "openalex_monthly.csv"))
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        columns = ["month", "metric", "status", "count", "cs_field_17_count", "unknown_field_count",
                   "query_sha256", "raw_sha256", "rule_version", "source"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"months": len(selected_months), "rows": len(rows),
                      "ok": sum(r["status"] == "ok" for r in rows),
                      "missing_or_invalid": sum(r["status"] != "ok" for r in rows),
                      "physical_calls": physical_call_count(audit_path), "csv": str(csv_path)}, ensure_ascii=False))


def diagnostics(output_dir: Path, max_calls: int):
    raw_dir = output_dir / "raw" / "openalex"
    audit_path = output_dir / "query_audit.jsonl"
    rows = []
    for month in ("2020-01", "2020-09", "2023-01", "2023-09", "2026-09"):
        for grouping in ("first_day", "type"):
            url = diagnostic_query(month, grouping)
            obj, raw_hash = fetch(url, raw_dir, audit_path, max_calls)
            if obj is None or (grouping != "first_day" and
                               (not isinstance(obj.get("group_by"), list) or obj["meta"].get("next_cursor"))):
                rows.append({"month": month, "group_by": grouping, "key": "", "count": "", "status": "missing",
                             "raw_sha256": raw_hash or ""})
                continue
            groups = [{"key": month + "-01", "count": obj["meta"]["count"]}] if grouping == "first_day" else obj["group_by"]
            for group in groups:
                rows.append({"month": month, "group_by": grouping, "key": group.get("key"),
                             "count": group.get("count"), "status": "ok", "raw_sha256": raw_hash})
    path = output_dir / "diagnostic_groups.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=("month", "group_by", "key", "count", "status", "raw_sha256"))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"diagnostic_rows": len(rows), "physical_calls": physical_call_count(audit_path),
                      "csv": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scope", choices=("pilot", "full", "first-day", "marketing-pilot", "marketing"), default="pilot")
    parser.add_argument("--max-calls", type=int, default=MAX_CALLS)
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    if args.diagnostics:
        diagnostics(args.output_dir, args.max_calls)
    else:
        selected = list(PILOT_MONTHS if args.scope == "pilot" else
                        ("2020-09", "2025-09") if args.scope == "marketing-pilot" else months(FIRST_MONTH, LAST_MONTH))
        marketing = args.scope in ("marketing-pilot", "marketing")
        metrics = (("marketing_primary_1406", "marketing_with_ai_vision_cotag") if marketing else
                   ("global_and_fields", "ai_primary_1702", "ai_vision_primary_1702_1707"))
        run(args.output_dir, selected, args.max_calls, first_day=args.scope == "first-day",
            metrics=metrics, output_name="openalex_marketing.csv" if marketing else None)
