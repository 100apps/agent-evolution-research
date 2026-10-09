#!/usr/bin/env python3
"""Fixed-seed ACL abstract review queue for narrow vs broad title-agent cues."""

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent
assign = {}
with (ROOT / "processed/shared_title_assignments.csv").open(encoding="utf-8-sig", newline="") as handle:
    for row in csv.DictReader(handle):
        if row["venue"] == "ACL" and row["year"] == "2025":
            assign[row["paper_id"]] = row
papers = [json.loads(line) for line in (ROOT / "nlp_vision/papers_main.jsonl").open(encoding="utf-8")
          if '"year": 2025' in line and '"venue": "ACL"' in line]
groups = {"narrow_title_candidate": [], "broad_agent_only": []}
for paper in papers:
    tags = (assign[paper["paper_id"]]["method_tags"] or "").split("|")
    if "explicit_lm_agent_title_candidate" in tags:
        groups["narrow_title_candidate"].append(paper)
    elif "agents_tools_broad" in tags:
        groups["broad_agent_only"].append(paper)
rng = random.Random(20261009)
rows = []
for group, pool in groups.items():
    for paper in rng.sample(pool, min(8, len(pool))):
        rows.append({"year": 2025, "venue": "ACL", "candidate_group": group,
                     "frame_n": len(pool), "sample_seed": 20261009,
                     "paper_id": paper["paper_id"], "title": paper["title"],
                     "abstract": paper["abstract"], "official_url": paper["official_url"],
                     "strict_loop_review": "unreviewed", "review_reason": ""})
path = ROOT / "processed/acl_agent_abstract_review.csv"
with path.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print({"rows": len(rows), "frames": {key: len(value) for key, value in groups.items()}})
