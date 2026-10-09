#!/usr/bin/env python3
"""Offline 61-column paper catalogue from frozen occurrences and metadata patch.

Rows are provisional work IDs: no title-only cross-source merge is performed.
Every classification is an unreviewed, title-rule candidate or an abstention.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

from source_records import ROOT, SOURCES, paper_uid, source_rows
from schema_validation import SCHEMA, validate_master_schema, validate_source_coverage_row

HERE = Path(__file__).resolve().parent
ATTENTION_FIELDS = (
    "citation_count", "citation_provider", "citation_as_of", "citation_status", "provider_work_id",
    "influential_citation_count", "publication_age_months",
    "view_count", "view_provider", "view_window", "view_as_of", "view_status",
    "download_count", "download_provider", "download_window", "download_as_of", "download_status",
    "peer_review_score_json", "peer_review_decision", "peer_review_rubric", "peer_review_count",
    "code_urls_json", "data_urls_json", "artifact_status", "reproducibility_evidence_json",
    "retraction_status", "correction_status", "attention_evidence_json",
)
FIELDS = [field["name"] for field in SCHEMA["fields"]] + list(ATTENTION_FIELDS)
ATTENTION_JSON = {"peer_review_score_json", "code_urls_json", "data_urls_json",
                  "reproducibility_evidence_json", "attention_evidence_json"}
STAMP = "2026-10-09T00:00:00Z"  # release snapshot date; not an invented retrieval date


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def read_patch(path: Path) -> dict[tuple[str, int, str, str], dict]:
    result = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            obj = json.loads(line)
            key = obj["venue"], int(obj["year"]), obj["track"], obj["source_paper_id"]
            if key in result:
                raise ValueError(f"duplicate metadata join key: {key}")
            result[key] = obj
    return result


def read_assignments(path: Path) -> dict[str, dict]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = row["paper_uid"]
            if key in result:
                raise ValueError(f"duplicate assignment: {key}")
            result[key] = row
    return result


def read_fallback(path: Path) -> dict[tuple[str, int, str], dict]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = row["venue"], int(row["year"]), row["paper_id"]
            if key in result:
                raise ValueError(f"duplicate fallback author source: {key}")
            result[key] = row
    return result


def field_provenance(source: dict, patch: dict, manifest: dict, fallback: dict | None):
    proof = dict(patch["field_provenance"])
    title_url = source.get("official_url") or source.get("source_url") or ""
    proof["title"] = {"status": "present_source_title", "source_url": title_url,
                      "source_hash": source.get("source_sha256", "")}
    for name in ("abstract", "authors", "institutions", "countries"):
        obj = dict(proof.get(name) or {})
        refs = obj.get("evidence") or []
        obj["evidence"] = [{**e, "source_sha256": manifest.get(e.get("source_ref"), {}).get("source_sha256", "")}
                           for e in refs]
        if name == "abstract" and source.get("abstract") and obj.get("status") == "missing":
            obj = {"status": "present_normalized_record", "source_url": source.get("source_url") or title_url,
                   "source_hash": source.get("source_sha256", "")}
        if name == "authors" and fallback and not patch["authors"]:
            obj = {"status": "source_ordered_local_snapshot", "source_url": title_url,
                   "source_file": fallback["author_source_file"], "source_sha256": fallback["author_source_sha256"]}
        if not obj.get("status"):
            obj = {"status": "missing", "missing_reason": "no_verified_source_field"}
        if obj["status"] == "missing" and not obj.get("missing_reason"):
            obj["missing_reason"] = "not_in_saved_sources"
        proof[name] = obj
    return proof


def fallback_authors(fallback: dict | None, occurrence_id: str):
    if not fallback:
        return []
    people = json.loads(fallback["authorships_json"] or "[]")
    result = []
    for pos, person in enumerate(people, 1):
        affs = []
        for field, temporal in (("affiliation", "paper_scoped_explicit"),
                                ("profile_institution", "publication_time_unverified")):
            if person.get(field):
                affs.append({"name": person[field], "temporal_status": temporal,
                             "country_code": "", "country_name": "", "country_status": "missing",
                             "country_missing_reason": "not_explicit_in_source"})
        result.append({"name": person["name"], "affiliations": affs,
                       "occurrence_id": occurrence_id, "author_position": pos})
    return result


def build(source: dict, patch: dict, assignment: dict, fallback: dict | None,
          taxonomy: dict, manifest: dict) -> dict:
    venue, year = source["venue"], int(source["year"])
    source_id = str(source.get("paper_id") or source.get("stable_id"))
    uid = paper_uid(venue, year, source_id)
    occ = patch["occurrence_id"]
    title = source["title"]
    abstract = source.get("abstract") or ""
    authors = list(patch["authors"])
    if not authors:
        authors = fallback_authors(fallback, occ)
    names = [author["name"] for author in authors if author.get("name")]
    # OSDI retains its ambiguous source text in authors_raw, not guessed names.
    rich = [{**a, "occurrence_id": occ, "author_position": i} for i, a in enumerate(authors, 1)]
    affs = [aff for author in authors for aff in author.get("affiliations", []) if aff.get("name")]
    paper_affs = [aff["name"] for aff in affs if aff.get("temporal_status") in
                  ("paper_scoped_explicit", "paper_explicit")]
    profiles = [aff["name"] for aff in affs if aff.get("temporal_status") == "publication_time_unverified"]
    institutions = list(dict.fromkeys(patch["institutions"] + [a["name"] for a in affs]))
    countries = list(dict.fromkeys(patch["countries"]))
    country_evidence = []
    for author in rich:
        for aff in author.get("affiliations", []):
            if aff.get("country_code"):
                country_evidence.append({"country_code": aff["country_code"],
                    "country_name": aff.get("country_name", ""),
                    "country_status": aff.get("country_status", ""),
                    "temporal_status": aff.get("temporal_status", ""),
                    "occurrence_id": occ, "author_position": author["author_position"],
                    "evidence_refs": patch["field_provenance"].get("countries", {}).get("evidence", [])})
    # Flat country codes are only the union of eligible paper-time affiliation evidence.
    countries = list(dict.fromkeys(e["country_code"] for e in country_evidence))
    leaves = list(dict.fromkeys(x for x in assignment["category_ids"].split("|") if
                                x and taxonomy[x]["level"] == 3))
    paths = [taxonomy[leaf]["path_ids"] for leaf in leaves]
    closure = {node for path in paths for node in path}
    raw_evidence = json.loads(assignment["classification_evidence"] or "[]")
    evidence = []
    for hit in raw_evidence:
        if hit["leaf_id"] not in leaves:
            continue
        start, end = hit["match_start"], hit["match_end"]
        if title[start:end] != hit["matched_text"]:
            raise ValueError(f"title evidence offset mismatch: {uid}")
        evidence.append({"category_id": hit["leaf_id"], "source_field": "title",
                         "source_url": source.get("official_url") or source.get("source_url"),
                         "span_start": start, "span_end": end, "quote": hit["matched_text"],
                         "assignment_role": "central_contribution",
                         "rationale_zh": "标题规则候选；核心贡献与语义仍待人工复核。",
                         "evidence_strength": "needs_review", "basis": "lexical_rule_candidate",
                         "rule_ids": [hit["rule_id"]], "review_status": "automated"})
    direct = patch.get("dedup_identifiers") or {}
    source_urls = list(dict.fromkeys(u for u in (source.get("official_url"), source.get("source_url")) if u))
    record_status = "provisional" if (venue == "NeurIPS" and year == 2026) else "observed"
    status = "classified" if leaves else "insufficient_evidence"
    proof = field_provenance(source, patch, manifest, fallback if not patch["authors"] else None)
    source_aff_count = sum(bool(a.get("affiliations")) for a in rich)
    paper_aff_count = sum(any(f.get("temporal_status") in ("paper_scoped_explicit", "paper_explicit")
                               for f in a.get("affiliations", [])) for a in rich)
    country_aff_count = sum(any(f.get("country_code") for f in a.get("affiliations", [])) for a in rich)
    completeness = "missing" if not rich else "complete" if source_aff_count == len(rich) else "partial" if source_aff_count else "missing"
    temporal = "mixed" if paper_affs and profiles else "paper_scoped" if paper_affs else "profile_time_unverified" if profiles else "missing"
    metadata_status = {k: ("present" if value else "missing") for k, value in
                       (("authors", rich), ("affiliations", affs), ("institutions", institutions),
                        ("countries", countries))}
    metadata_status["institution_ids"] = "not_checked"
    missing = {k: ("" if v == "present" else "not_in_saved_source_or_not_structured") for k, v in metadata_status.items()}
    coverage = {"author_slots_total": len(rich) if rich else None,
                "author_slots_structured": len(names),
                "author_slots_with_any_affiliation": source_aff_count,
                "author_slots_with_publication_affiliation": paper_aff_count,
                "author_slots_with_explicit_country": country_aff_count,
                "scope": "occurrence"}
    row = {
      "paper_id": patch["paper_entity_id"], "title": title, "abstract": abstract,
      "authors_json": names if names else None,
      "doi": direct.get("doi", ""), "arxiv_id": direct.get("arxiv_id", ""),
      "openreview_id": direct.get("openreview_id", ""),
      "official_url": source.get("official_url") or "", "source_urls_json": source_urls,
      "publication_year": year, "year_basis": "conference_edition_year_not_publication_date",
      "venues_json": [venue], "occurrence_ids_json": [occ],
      "occurrences_json": [{"occurrence_id": occ, "venue": venue, "year": year,
                            "track": source.get("track") or "", "source_id": source_id,
                            "source_url": source.get("source_url") or "",
                            "coverage_status": record_status,
                            "publication_date": patch.get("publication_date") or "",
                            "date_precision": patch.get("date_precision") or ""}],
      "dedup_status": "unresolved", "dedup_evidence_json": [{"type": k, "value": v} for k, v in direct.items()],
      "field_provenance_json": proof,
      "abstract_status": "present" if abstract else "missing", "abstract_char_count": len(abstract),
      "coverage_flags_json": ["provisional_conference_program"] if record_status == "provisional" else [],
      "classification_status": status,
      "classification_label_status": "candidate" if leaves else "unassigned",
      "classification_method": "frozen_title_regex_candidates_not_semantic_review",
      "classifier_version": "cake-title-rules-v1.1.0-proposed",
      "taxonomy_version": assignment["taxonomy_version"], "classified_at": "",
      "classification_basis": "title_only",
      "classification_input_fields_json": [{"field": "title", "sha256": hashlib.sha256(title.encode("utf-8")).hexdigest()}],
      "classification_reason": "标题词项命中；语义待复核" if leaves else "标题规则未命中；不等于非AI",
      "review_status": "automated", "review_notes": "",
      "category_ids_l1_json": [i for i in taxonomy if taxonomy[i]["level"] == 1 and i in closure],
      "category_ids_l2_json": [i for i in taxonomy if taxonomy[i]["level"] == 2 and i in closure],
      "category_ids_l3_json": leaves, "category_paths_json": paths,
      "category_paths_text": assignment["category_paths"],
      "category_evidence_json": evidence, "facets_json": None,
      "facet_evidence_json": [], "candidate_topics_json": [],
      "label_warnings_json": list(patch.get("warnings", [])) + (["title_rule_candidate_not_reviewed"] if leaves else []),
      "retrieved_at": source.get("source_fetched_at_utc") or source.get("retrieved_at") or "",
      "record_updated_at": STAMP,
      "authors_raw": source.get("authors") if isinstance(source.get("authors"), str) else compact(source.get("authors")) if source.get("authors") else "",
      "author_affiliations_json": rich if rich else None,
      "institutions_json": institutions if institutions else None,
      "publication_affiliations_json": list(dict.fromkeys(paper_affs)) if paper_affs else None,
      "profile_affiliations_json": list(dict.fromkeys(profiles)) if profiles else None,
      "unlinked_affiliations_json": None, "institution_entities_json": None,
      "countries_json": countries if countries else None,
      "country_evidence_json": country_evidence if country_evidence else None,
      "author_affiliation_completeness": completeness if rich else "unstructured" if source.get("authors") else "missing",
      "affiliation_temporal_status": temporal,
      "institution_resolution_status": "not_checked" if institutions else "missing",
      "country_coverage_status": "partial" if countries else "missing",
      "metadata_field_status_json": metadata_status,
      "metadata_missing_reasons_json": missing,
      "metadata_field_coverage_json": coverage,
      "metadata_occurrence_provenance_json": [{"occurrence_id": occ, "field_provenance": patch["field_provenance"]}],
      "metadata_audit_version": "local-snapshot-adapted-1.0.0",
    }
    # No third-party metric was fetched for this frozen first edition. Missing
    # metrics are unknown, never zero; no quality score is fabricated.
    row.update({name: (None if name in ATTENTION_JSON else "") for name in ATTENTION_FIELDS})
    row.update(citation_status="not_collected", view_status="not_available",
               download_status="not_available", artifact_status="not_checked",
               retraction_status="not_checked", correction_status="not_checked",
               attention_evidence_json=[])
    date = patch.get("publication_date") or ""
    if patch.get("date_precision") in ("month", "day") and len(date) >= 7:
        y, m = int(date[:4]), int(date[5:7])
        row["publication_age_months"] = max(0, (2026 - y) * 12 + 10 - m)
    return row


def csv_row(row: dict) -> dict[str, str]:
    result = {}
    for key in FIELDS:
        value = row[key]
        if key.endswith("_json") or key in ATTENTION_JSON:
            result[key] = compact(value)
        else:
            result[key] = str(value)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--fallback-authors", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Output directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    patch = read_patch(args.patch)
    assignments = read_assignments(args.assignments)
    fallback = read_fallback(args.fallback_authors)
    manifest_data = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    manifest = {entry["source_id"]: entry for entry in manifest_data["sources"]}
    taxonomy_obj = json.loads((HERE / "taxonomy.json").read_text(encoding="utf-8"))
    taxonomy = {node["id"]: node for node in taxonomy_obj["nodes"]}
    counts = Counter()
    seen = set()
    coverage = Counter()
    master_path = output / "master_papers.csv"
    occurrence_path = output / "paper_occurrences.csv"
    with master_path.open("w", encoding="utf-8-sig", newline="") as master_stream, occurrence_path.open("w", encoding="utf-8-sig", newline="") as occ_stream:
        writer = csv.DictWriter(master_stream, fieldnames=FIELDS)
        writer.writeheader()
        occ_writer = csv.DictWriter(occ_stream, fieldnames=["paper_id", "occurrence_id", "venue", "year", "track", "source_record_id", "status"])
        occ_writer.writeheader()
        for relative, line, source in source_rows():
            venue, year = source["venue"], int(source["year"])
            sid = str(source.get("paper_id") or source.get("stable_id"))
            key = venue, year, source.get("track") or "", sid
            if key not in patch:
                raise ValueError(f"missing exact-key metadata patch: {key}")
            uid = paper_uid(venue, year, sid)
            if uid not in assignments:
                raise ValueError(f"missing assignment: {uid}")
            row = build(source, patch[key], assignments[uid], fallback.get((venue, year, sid)), taxonomy, manifest)
            if row["paper_id"] in seen:
                raise ValueError(f"duplicate provisional paper_id requires work aggregation: {row['paper_id']}")
            seen.add(row["paper_id"])
            errors = validate_master_schema(row)
            if errors:
                raise ValueError(f"schema validation failed for {key}: {errors[:8]}")
            writer.writerow(csv_row(row))
            occ_writer.writerow({"paper_id": row["paper_id"], "occurrence_id": patch[key]["occurrence_id"],
                                 "venue": venue, "year": year, "track": key[2], "source_record_id": sid,
                                 "status": row["coverage_flags_json"][0] if row["coverage_flags_json"] else "observed"})
            counts[(venue, year)] += 1
            for name, value in (("authors", row["authors_json"]), ("institutions", row["institutions_json"]),
                                ("paper_institutions", row["publication_affiliations_json"]),
                                ("countries", row["countries_json"]), ("candidate", row["category_ids_l3_json"])):
                coverage[name] += bool(value)
    if len(seen) != 89530 or len(patch) != 89530 or len(assignments) != 89530:
        raise ValueError("expected 89,530 exact source occurrence joins")
    coverage_path = output / "source_coverage_manifest.csv"
    with coverage_path.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = SCHEMA["source_coverage_manifest_contract"]["required_columns"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for venue in sorted({v for v, y in counts}):
            for year in range(2020, 2027):
                n = counts[(venue, year)]
                row = {"source_scope_id": f"{venue}:{year}:main", "venue": venue, "year": year,
                       "track": "main_or_source_track", "event_status": "unknown",
                       "collection_status": "partial" if venue == "NeurIPS" and year == 2026 else "unknown" if n else "not_collected",
                       "observed_occurrences": n, "announced_expected_count": "",
                       "field_coverage_json": "{}", "coverage_notes": "可见来源记录；未证明全量覆盖" if n else "本目录未采集；不是零论文",
                       "source_url": "", "retrieved_at": ""}
                if (issues := validate_source_coverage_row(row)):
                    raise ValueError(issues)
                writer.writerow(row)
    with master_path.open("rb") as source, (output / "master_papers.csv.gz").open("wb") as dest:
        with gzip.GzipFile(filename="", mode="wb", fileobj=dest, compresslevel=9, mtime=0) as archive:
            for chunk in iter(lambda: source.read(1 << 20), b""):
                archive.write(chunk)
    receipt = {"schema_version": SCHEMA["schema_version"], "attention_extension": "attention-v1.0.0",
               "rows": len(seen), "columns": len(FIELDS),
               "unit": "provisional work IDs; duplicate resolution incomplete",
               "coverage": dict(coverage), "csv_bytes": master_path.stat().st_size,
               "csv_sha256": sha(master_path), "gzip_bytes": (output / "master_papers.csv.gz").stat().st_size,
               "gzip_sha256": sha(output / "master_papers.csv.gz"),
               "input_hashes": {"patch": sha(args.patch), "source_manifest": sha(args.source_manifest),
                                "assignments": sha(args.assignments), "fallback_authors": sha(args.fallback_authors),
                                "taxonomy": sha(HERE / "taxonomy.json"), "schema": sha(HERE / "master_csv_schema.json")},
               "validation": "all rows passed independent 61-field schema gate; semantic labels remain candidates"}
    (output / "master_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
