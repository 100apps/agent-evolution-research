#!/usr/bin/env python3
"""Apply one frozen, overlapping title lexicon to five official conference corpora."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
RULE_PATH = ROOT / "shared_title_rules.json"
OUT = ROOT / "processed"


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"empty result {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def records(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def normalized(value):
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def run():
    rule_raw = RULE_PATH.read_bytes()
    rule_hash = hashlib.sha256(rule_raw).hexdigest()
    spec = json.loads(rule_raw)
    methods = {key: re.compile(pattern) for key, pattern in spec["method_tags"].items()}
    tasks = {key: re.compile(pattern) for key, pattern in spec["task_tags"].items()}
    source_rows = list(records(ROOT / "nlp_vision" / "papers_main.jsonl"))
    source_rows += list(records(ROOT / "ml" / "metadata_main.jsonl"))
    assignments = []
    cohorts = defaultdict(list)
    for item in source_rows:
        title = normalized(item["title"])
        method = sorted(key for key, rx in methods.items() if rx.search(title))
        task = sorted(key for key, rx in tasks.items() if rx.search(title))
        if "explicit_language_foundation" in method and "agents_tools_broad" in method:
            method.append("explicit_lm_agent_title_candidate")
        record = {"venue": item["venue"], "year": int(item["year"]), "paper_id": item["paper_id"],
                  "title": item["title"], "official_url": item["official_url"],
                  "source_type": item["source_type"], "method_tags": method, "task_tags": task,
                  "rule_sha256": rule_hash}
        assignments.append(record)
        cohorts[(item["venue"], int(item["year"]))].append(record)
    if len(assignments) != 83337:
        raise ValueError(f"unexpected cross-source paper count {len(assignments)}")
    if len(assignments) != len({(row["venue"], row["year"], row["paper_id"]) for row in assignments}):
        raise ValueError("duplicate venue-year paper IDs")
    for year in range(2020, 2026):
        cohorts[("ML_three", year)] = [row for row in assignments if row["year"] == year
                                      and row["venue"] in ("ICML", "ICLR", "NeurIPS")]
    for year in range(2020, 2027):
        cohorts[("ML_ICML_ICLR", year)] = [row for row in assignments if row["year"] == year
                                          and row["venue"] in ("ICML", "ICLR")]
    labels = [*methods, "explicit_lm_agent_title_candidate", *tasks]
    yearly, crosses = [], []
    for (venue, year), group in sorted(cohorts.items()):
        n = len(group)
        if not n:
            continue
        status = "provisional_incomplete" if venue == "NeurIPS" and year == 2026 else "source_defined_main"
        for label in labels:
            axis = "task" if label in tasks else "method"
            count = sum(label in row[axis + "_tags"] for row in group)
            yearly.append({"cohort": venue, "year": year, "source_status": status,
                           "axis": axis, "tag": label, "matching_titles": count,
                           "denominator_papers": n, "share_pct": round(100 * count / n, 6),
                           "rule_sha256": rule_hash})
        for task in tasks:
            task_rows = [row for row in group if task in row["task_tags"]]
            for method in [*methods, "explicit_lm_agent_title_candidate"]:
                count = sum(method in row["method_tags"] for row in task_rows)
                crosses.append({"cohort": venue, "year": year, "source_status": status,
                                "task_tag": task, "method_tag": method,
                                "both_titles": count, "task_titles": len(task_rows),
                                "denominator_papers": n,
                                "share_of_task_pct": round(100 * count / len(task_rows), 6) if task_rows else None,
                                "rule_sha256": rule_hash})
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "shared_title_yearly.csv", yearly)
    write_csv(OUT / "shared_title_cross.csv", crosses)
    write_csv(OUT / "shared_title_assignments.csv", [
        {**row, "method_tags": "|".join(row["method_tags"]), "task_tags": "|".join(row["task_tags"])}
        for row in assignments])
    rng = random.Random(20261009)
    review = []
    for year in (2020, 2023, 2025, 2026):
        for label in ("explicit_language_foundation", "agents_tools_broad",
                      "explicit_lm_agent_title_candidate", "search_retrieval",
                      "recommendation", "software_code"):
            axis = "task_tags" if label in tasks else "method_tags"
            pool = [row for row in assignments if row["year"] == year and label in row[axis]
                    and not (row["venue"] == "NeurIPS" and year == 2026)]
            for item in rng.sample(pool, min(8, len(pool))):
                review.append({"year": year, "sampled_tag": label, "sample_frame_n": len(pool),
                               "sample_seed": 20261009, "venue": item["venue"], "paper_id": item["paper_id"],
                               "title": item["title"], "official_url": item["official_url"],
                               "semantic_review": "unreviewed", "rule_sha256": rule_hash})
    write_csv(OUT / "shared_title_review_queue.csv", review)
    result = {"rule_version": spec["version"], "rule_sha256": rule_hash,
              "venue_year_records": len(assignments), "yearly_rows": len(yearly),
              "cross_rows": len(crosses), "review_queue_rows": len(review)}
    (OUT / "shared_title_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    run()
