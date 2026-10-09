"""Stable identities and frozen local conference corpus readers."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCES=("conferences/ml/metadata_main.jsonl",
         "conferences/nlp_vision/papers_main.jsonl",
         "conferences/systems_ir/combined_papers.jsonl")

def paper_uid(venue: str, year: int, record_id: str) -> str:
    return "conference:"+hashlib.sha256(f"{venue}\0{year}\0{record_id}".encode("utf-8")).hexdigest()[:24]

def source_rows():
    for relative in SOURCES:
        with (ROOT/relative).open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():yield relative,line,json.loads(line)
