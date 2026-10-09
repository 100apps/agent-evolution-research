#!/usr/bin/env python3
"""Make a compact, streamable browser index from the complete master CSV."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path


INDEX_FIELDS = (
    "paper_uid", "work_uid", "venue", "conference_year", "title", "paper_url",
    "paper_url_kind", "authors", "paper_affiliations", "profile_institutions_unverified",
    "affiliation_countries", "category_ids", "category_paths", "classification_status",
    "classification_evidence", "classification_rule_ids", "classification_method",
    "taxonomy_version", "record_status", "source_record_id", "source_corpus",
    "doi_reported", "doi_basis", "included_in_main_trends", "dedup_status",
    "country_coverage_status", "authors_raw", "metadata_audit_version",
    "citation_count", "citation_status", "view_count", "view_status",
    "publication_age_days", "artifact_status", "retraction_status",
    "citation_provider", "citation_as_of", "doi_status", "authors_status",
    "classification_label_status", "review_status", "track", "audit_ref",
)


def transform(row: dict[str, str]) -> dict[str, str]:
    """Compact view over validated v1.1 master; never replace the source CSV."""
    def array(name):
        return json.loads(row[name]) or []
    occurrence = array("occurrences_json")[0]
    authors = array("authors_json")
    impact = json.loads(row["impact_metrics_json"])
    states = impact["collection_status"]
    integrity = impact["integrity_events"]
    proof = json.loads(row["field_provenance_json"])
    metadata = json.loads(row["metadata_field_status_json"])
    doi_status = (proof.get("doi") or {}).get("status") or "missing"
    if not row["doi"] and doi_status != "missing":
        doi_status = "reported_but_not_verified_for_export"
    names_status = "unstructured_source_text" if not authors and row["authors_raw"] else metadata["authors"]
    return {
        "paper_uid": array("occurrence_ids_json")[0],
        "work_uid": row["paper_id"],
        "venue": occurrence["venue"], "conference_year": str(occurrence["year"]),
        "title": row["title"], "paper_url": row["official_url"],
        "paper_url_kind": "official_source", "authors": "; ".join(authors),
        "paper_affiliations": "; ".join(array("publication_affiliations_json")),
        "profile_institutions_unverified": "; ".join(array("profile_affiliations_json")),
        "affiliation_countries": "; ".join(array("countries_json")),
        "category_ids": "|".join(array("category_ids_l1_json") + array("category_ids_l2_json") + array("category_ids_l3_json")),
        "category_paths": row["category_paths_text"],
        "classification_status": "title_rule_candidate" if row["classification_label_status"] == "candidate" else row["classification_status"],
        "classification_evidence": row["category_evidence_json"],
        "classification_rule_ids": "|".join(sorted({rule for e in array("category_evidence_json") for rule in e.get("rule_ids", [])})),
        "classification_method": row["classification_method"],
        "taxonomy_version": row["taxonomy_version"],
        "record_status": "provisional" if "provisional_conference_program" in array("coverage_flags_json") else "observed",
        "source_record_id": occurrence["source_id"],
        "source_corpus": occurrence["venue"], "doi_reported": row["doi"],
        "doi_basis": "verified_exact_identifier" if row["doi"] else "missing",
        "included_in_main_trends": "false" if "provisional_conference_program" in array("coverage_flags_json") else "true",
        "dedup_status": row["dedup_status"], "country_coverage_status": row["country_coverage_status"],
        "authors_raw": row["authors_raw"], "metadata_audit_version": row["metadata_audit_version"],
        "citation_count": row["citation_count"], "citation_status": row["citation_status"],
        "view_count": row["views_count"], "view_status": states["views"]["status"],
        "publication_age_days": row["publication_age_days"],
        "artifact_status": states["artifacts"]["status"],
        "retraction_status": integrity[0]["assertion"] if integrity else "not_checked",
        "citation_provider": row["citation_provider"],
        "citation_as_of": row["citation_as_of"],
        "doi_status": doi_status, "authors_status": names_status,
        "classification_label_status": row["classification_label_status"],
        "review_status": row["review_status"], "track": occurrence["track"],
        "audit_ref": "master_papers.csv#paper_id=" + row["paper_id"],
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Output directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    data_path = output / "papers_index.jsonl.gz"
    counts = Counter()
    works = set()
    with args.master.open(encoding="utf-8-sig", newline="") as source, data_path.open("wb") as compressed:
        reader = csv.DictReader(source)
        missing = {"paper_id", "title", "occurrences_json", "authors_json", "category_ids_l1_json",
                   "category_ids_l2_json", "category_ids_l3_json", "classification_label_status"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"master CSV lacks index fields: {sorted(missing)}")
        with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, compresslevel=9, mtime=0) as archive:
            with io.TextIOWrapper(archive, encoding="utf-8", newline="\n") as text:
                for row in reader:
                    view = transform(row)
                    text.write(json.dumps([view[field] for field in INDEX_FIELDS], ensure_ascii=False,
                                          separators=(",", ":")) + "\n")
                    counts["rows"] += 1
                    counts["venue:" + view["venue"]] += 1
                    counts["status:" + view["classification_status"]] += 1
                    for country in json.loads(row["countries_json"]) or []:
                        counts["country:" + country] += 1
                    counts["citation:present"] += bool(row["citation_count"])
                    works.add(view["work_uid"])
    if counts["rows"] != 89530:
        raise ValueError(f"unexpected explorer row count: {counts['rows']}")
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8")) if args.taxonomy else None
    manifest = {
        "schema_version": "conference-explorer-index-v1",
        "row_unit": "conference venue-year record",
        "row_count": counts["rows"],
        "provisional_work_ids": len(works),
        "columns": list(INDEX_FIELDS),
        "data_file": data_path.name,
        "data_bytes": data_path.stat().st_size,
        "data_sha256": sha256(data_path),
        "master_csv_sha256": sha256(args.master),
        "counts": dict(sorted(counts.items())),
        "taxonomy": taxonomy,
        "notes": [
            "Category labels may overlap; a paper counts once within each selected category.",
            "Country is blank unless explicitly stated in saved source metadata.",
            "NeurIPS 2026 provisional records are excluded by default in the browser.",
        ],
    }
    (output / "index_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps({"row_count": counts["rows"], "work_ids": len(works),
                      "data_bytes": data_path.stat().st_size, "sha256": manifest["data_sha256"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
