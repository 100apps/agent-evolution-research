#!/usr/bin/env python3
"""Analyze cached arXiv count queries without mixing them with OpenAlex works."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from analyze_openalex import ratio, write_csv
from collect_arxiv import months


def load(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = [(row["month"], row["metric"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate month/metric in {path}")
    return dict(zip(keys, rows))


def value(rows: dict, month: str, metric: str) -> int | None:
    row = rows.get((month, metric))
    if not row or row["status"] != "ok" or row["count"] == "":
        return None
    return int(row["count"])


def analyze(data_dir: Path) -> dict:
    source = load(data_dir / "arxiv_monthly.csv")
    pilot = load(data_dir / "arxiv_pilot.csv") if (data_dir / "arxiv_pilot.csv").exists() else {}
    internal_path = data_dir / "arxiv_internal_monthly.csv"
    internal = load(internal_path) if internal_path.exists() else {}
    internal_pilot_path = data_dir / "arxiv_internal_pilot.csv"
    internal_pilot = load(internal_pilot_path) if internal_pilot_path.exists() else {}
    internal_metrics = sorted({metric for _, metric in [*internal, *internal_pilot]})
    rows = []
    for month in months():
        all_count = value(source, month, "all_arxiv")
        cs_stat = value(source, month, "cs_plus_stat_ml")
        core = value(source, month, "core_ai_5_category_proxy")
        cs_only = value(pilot, month, "cs_only")
        core_in_cs = value(pilot, month, "core_ai_5_in_cs")
        if all(v is not None for v in (all_count, cs_stat, core)) and not core <= cs_stat <= all_count:
            raise ValueError(f"unexpected arXiv nesting: {month}")
        row = {"month": month, "all_arxiv_submissions": all_count,
               "cs_plus_stat_ml_submissions": cs_stat, "core_ai_5_submissions": core,
               "core_ai_5_share_all_pct": ratio(core, all_count),
               "core_ai_5_share_cs_plus_stat_ml_pct": ratio(core, cs_stat),
               "cs_only_submissions_pilot": cs_only,
               "core_ai_5_in_cs_submissions_pilot": core_in_cs,
               "core_ai_5_in_cs_share_cs_pilot_pct": ratio(core_in_cs, cs_only),
               "recent_within_12m": month >= "2025-10",
               "status": "ok" if all(v is not None for v in (all_count, cs_stat, core)) else "missing",
               "date_semantics": "arXiv API submittedDate UTC",
               "scope_version": "arxiv-core5-v1.0.2"}
        for metric in internal_metrics:
            count = value(internal, month, metric)
            if count is None:
                count = value(internal_pilot, month, metric)
            row[metric + "_candidate_hits"] = count
            row[metric + "_share_core5_pct"] = ratio(count, core)
        rows.append(row)
    processed = data_dir / "processed"
    write_csv(processed / "arxiv_monthly_wide.csv", rows, list(rows[0]))
    annual = []
    for year in range(2020, 2027):
        members = [row for row in rows if row["month"].startswith(str(year))]
        complete = len(members) == 12 and all(row["status"] == "ok" for row in members)
        result = {"year": year, "calendar_months_observed": len(members),
                  "status": "ok" if complete else "partial_or_missing"}
        for key in ("all_arxiv_submissions", "cs_plus_stat_ml_submissions", "core_ai_5_submissions"):
            result[key] = sum(row[key] for row in members) if complete else None
        result["core_ai_5_share_all_pct"] = ratio(result["core_ai_5_submissions"], result["all_arxiv_submissions"])
        result["core_ai_5_share_cs_plus_stat_ml_pct"] = ratio(result["core_ai_5_submissions"], result["cs_plus_stat_ml_submissions"])
        for metric in internal_metrics:
            key = metric + "_candidate_hits"
            result[key] = (sum(row[key] for row in members)
                           if complete and all(row[key] is not None for row in members) else None)
            result[metric + "_share_core5_pct"] = ratio(result[key], result["core_ai_5_submissions"])
        annual.append(result)
    write_csv(processed / "arxiv_annual.csv", annual, list(annual[0]))
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "months_expected": len(rows), "months_ok": sum(row["status"] == "ok" for row in rows),
               "annual": annual, "pilot_same_months": [row for row in rows if row["month"] in ("2020-09", "2023-09", "2026-09")],
               "internal_metrics": internal_metrics,
               "caution": "Counts are arXiv query/category or title-abstract keyword candidates, not authors or semantic paper labels."}
    (processed / "arxiv_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(analyze(Path("research_trends/data")), ensure_ascii=False))
