#!/usr/bin/env python3
"""Conservative post-sampling screen for obvious non-AI works in one fixed-seed sample."""

from __future__ import annotations

import csv
from pathlib import Path

DATA = Path("research_trends/data")
OBVIOUS = {
    "Quantum steering with rotation-invariant": "quantum nonlocality physics",
    "Iso-dip Contouring:": "uranium mineral exploration",
    "High-dimensional quantum key distribution": "quantum cryptography",
    "Probabilistic coherence distillation": "quantum coherence",
    "Italien : Structures de la langue": "linguistics textbook",
    "Classification of extremal type II": "algebraic coding theory",
    "On a gap in the proof of the generalised quantum Stein": "quantum information theory",
    "Qubit Recycling in Entanglement Distillation": "quantum entanglement",
    "Multifractal Characteristics of Uranium Grade": "uranium geology",
    "Practical robust Bayesian spin-squeezing": "quantum sensing",
    "Covert Communication and Key Generation Over Quantum": "quantum communication",
    "LWLCM: A novel lightweight stream cipher": "cipher design",
    "Reliable RSA Cryptosystem Using the Path": "classical cryptosystem",
}


def run():
    with (DATA / "openalex_metadata_sample.csv").open(encoding="utf-8-sig", newline="") as handle:
        source = [row for row in csv.DictReader(handle) if row["stratum"] == "ai_primary"]
    if len(source) != 60:
        raise ValueError(f"expected 60 fixed-seed AI-stratum titles, got {len(source)}")
    rows = []
    matched = set()
    for row in source:
        hits = [(prefix, reason) for prefix, reason in OBVIOUS.items() if row["title"].startswith(prefix)]
        if len(hits) > 1:
            raise ValueError("ambiguous matching prefixes")
        if hits:
            matched.add(hits[0][0])
        rows.append({"month": row["month"], "work_id": row["work_id"], "title": row["title"],
                     "sample_seed": row["sample_seed"], "sample_stratum": row["stratum"],
                     "screen": "obvious_non_ai" if hits else "not_adjudicated",
                     "reason": hits[0][1] if hits else "",
                     "basis": "title and available abstract; conservative screen, not expert validation",
                     "query_sha256": row["query_sha256"], "raw_sha256": row["raw_sha256"]})
    if matched != set(OBVIOUS):
        raise ValueError(f"unmatched review anchors: {set(OBVIOUS)-matched}")
    path = DATA / "openalex_ai_sample_screen.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print({"sample_n": len(rows), "obvious_non_ai": sum(row["screen"] == "obvious_non_ai" for row in rows),
           "unresolved": sum(row["screen"] == "not_adjudicated" for row in rows)})


if __name__ == "__main__":
    run()
