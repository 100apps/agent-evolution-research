#!/usr/bin/env python3
"""Document one conservative model-assisted abstract screen; no expert ground truth."""

import csv
from pathlib import Path

ROOT = Path(__file__).parent
REVIEW = {
    "2025.acl-long.672": ("related_no_loop_demonstrated", "attack on a tool-using LLM system; abstract does not establish the proposed method as an agent loop"),
    "2025.acl-long.1266": ("loop_supported", "ToolMaker installs, writes and executes code, then self-corrects in a closed loop"),
    "2025.acl-long.369": ("related_no_loop_demonstrated", "survey of OS agents rather than a tested new loop in this paper"),
    "2025.acl-long.1202": ("uncertain", "multi-agent graph exploration described, but abstract excerpt does not establish a tool-observation-feedback cycle"),
    "2025.acl-long.1490": ("related_no_loop_demonstrated", "benchmark compares agents; the paper's contribution is the benchmark"),
    "2025.acl-long.1136": ("uncertain", "multi-agent scenario and data simulation, external environment feedback not clear"),
    "2025.acl-long.874": ("loop_supported", "ToolCoder creates and executes tool code, with error diagnosis and reflection"),
    "2025.acl-long.476": ("related_no_loop_demonstrated", "attack on multi-agent communication, not a demonstrated task-environment loop"),
    "2025.acl-long.829": ("uncertain", "dynamic content-extraction agent, but loop semantics not explicit"),
    "2025.acl-long.221": ("uncertain", "finite-state collection/analysis framework; external observation feedback not explicit"),
    "2025.acl-long.1354": ("loop_supported", "self-evolving LLM agent modifies its logic/behavior against task feedback"),
    "2025.acl-short.33": ("loop_supported", "explicit multi-step environment actions and search-based refinement"),
    "2025.acl-long.945": ("related_no_loop_demonstrated", "reward-model-guided answer search; no tool/environment execution loop"),
    "2025.acl-long.468": ("loop_supported", "LLM selects KG tools and updates memory iteratively"),
    "2025.acl-long.642": ("uncertain", "multiple roles generate instruction data, but environment feedback not explicit"),
    "2025.acl-long.46": ("related_no_loop_demonstrated", "multi-agent debate for classification, no external environment action loop"),
}
source = ROOT / "processed/acl_agent_abstract_review.csv"
with source.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
if set(row["paper_id"] for row in rows) != set(REVIEW):
    raise ValueError("review labels do not match frozen random sample IDs")
for row in rows:
    row["strict_loop_review"], row["review_reason"] = REVIEW[row["paper_id"]]
    row["review_basis"] = "assistant title+abstract screen only; not independent human expert validation"
out = ROOT / "processed/acl_agent_abstract_reviewed.csv"
with out.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
from collections import Counter
print(dict(Counter((row["candidate_group"], row["strict_loop_review"]) for row in rows)))
