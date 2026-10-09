#!/usr/bin/env python3
"""Assign conservative, overlapping three-level taxonomy candidates from titles."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from source_records import ROOT, paper_uid, source_rows


HERE = Path(__file__).resolve().parent
FIELDS = ("paper_uid", "category_ids", "category_paths", "classification_status",
          "classification_evidence", "classification_rule_ids", "classification_method",
          "taxonomy_version")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path, default=HERE / "taxonomy.json")
    parser.add_argument("--rules", type=Path, default=HERE / "title_rules.json")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Output directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    rulebook = json.loads(args.rules.read_text(encoding="utf-8"))
    if rulebook["taxonomy_version"] != taxonomy["version"]:
        raise ValueError("rulebook targets a different taxonomy version")
    nodes = {node["id"]: node for node in taxonomy["nodes"]}
    order = {node["id"]: index for index, node in enumerate(taxonomy["nodes"])}
    leaves = {node_id for node_id, node in nodes.items() if node["level"] == 3}
    rules = []
    seen_rules = set()
    for rule in rulebook["rules"]:
        if rule["id"] in seen_rules or rule["leaf_id"] not in leaves:
            raise ValueError(f"invalid or duplicated taxonomy rule: {rule['id']}")
        seen_rules.add(rule["id"])
        rules.append((rule, [re.compile(pattern, re.IGNORECASE) for pattern in rule["any"]]))
    if len(rules) != len(leaves) or {rule["leaf_id"] for rule, _ in rules} != leaves:
        raise ValueError("title rule inventory must cover each of the 59 frozen leaves once")
    counts = Counter()
    year_counts = Counter()
    seen = set()
    destination = output / "title_assignments.csv"
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for _, _, source in source_rows():
            venue, year = source["venue"], int(source["year"])
            record_id = str(source.get("paper_id") or source.get("stable_id"))
            uid = paper_uid(venue, year, record_id)
            if uid in seen:
                raise ValueError(f"duplicate source UID: {uid}")
            seen.add(uid)
            # Evidence offsets must address the exact stored title, including
            # any original Unicode compatibility characters.
            title = source["title"]
            matched = []
            for rule, patterns in rules:
                hit = next((match for pattern in patterns if (match := pattern.search(title))), None)
                if hit:
                    matched.append((rule, hit))
            leaf_ids = sorted({rule["leaf_id"] for rule, _ in matched}, key=order.get)
            category_ids = sorted({ancestor for leaf_id in leaf_ids
                                   for ancestor in nodes[leaf_id]["path_ids"]}, key=order.get)
            category_paths = [" / ".join(nodes[node_id]["label_zh"]
                                         for node_id in nodes[leaf_id]["path_ids"])
                              for leaf_id in leaf_ids]
            evidence = [{"leaf_id": rule["leaf_id"], "rule_id": rule["id"],
                         "field": "title", "matched_text": hit.group(0),
                         "match_start": hit.start(), "match_end": hit.end()}
                        for rule, hit in matched]
            status = "title_rule_candidate" if matched else "insufficient_evidence"
            writer.writerow({
                "paper_uid": uid,
                "category_ids": "|".join(category_ids),
                "category_paths": " | ".join(category_paths),
                "classification_status": status,
                "classification_evidence": json.dumps(evidence, ensure_ascii=False,
                                                      separators=(",", ":")) if evidence else "",
                "classification_rule_ids": "|".join(rule["id"] for rule, _ in matched),
                "classification_method": "title_regex_candidate_not_semantic_review",
                "taxonomy_version": taxonomy["version"],
            })
            counts[status] += 1
            for leaf_id in leaf_ids:
                counts["leaf:" + leaf_id] += 1
                year_counts[(year, leaf_id)] += 1
            for layer in {leaf_id.split(".")[0] for leaf_id in leaf_ids}:
                counts["layer:" + layer] += 1
    if len(seen) != 89530:
        raise ValueError(f"unexpected source inventory: {len(seen)}")
    receipt = {
        "status": "ok", "rows": len(seen),
        "taxonomy_version": taxonomy["version"], "taxonomy_sha256": sha256(args.taxonomy),
        "rule_version": rulebook["version"], "rule_sha256": sha256(args.rules),
        "assignments_sha256": sha256(destination),
        "method": "title-only lexical candidates; not full-text semantic labels",
        "counts": dict(sorted(counts.items())),
        "year_leaf_counts": [{"year": year, "leaf_id": leaf, "records": count}
                             for (year, leaf), count in sorted(year_counts.items())],
        "unmatched_policy": "insufficient_evidence; no automatic outside_scope or taxonomy_gap inference",
    }
    (output / "title_assignments_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: receipt[key] for key in ("status", "rows", "taxonomy_version",
                                                  "rule_version", "assignments_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
