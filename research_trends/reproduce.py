#!/usr/bin/env python3
"""Validate captured trend evidence and rebuild derived files without network access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DETERMINISTIC_OUTPUTS = (
    "data/processed/openalex_monthly_wide.csv",
    "data/processed/openalex_annual.csv",
    "data/processed/openalex_fields_monthly.csv",
    "data/processed/arxiv_monthly_wide.csv",
    "data/processed/arxiv_annual.csv",
    "conferences/nlp_vision/papers_main.jsonl",
    "conferences/ml/metadata_main.jsonl",
    "conferences/processed/shared_title_yearly.csv",
    "conferences/processed/shared_title_cross.csv",
    "reports/dashboard.html",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON at {path}:{number}") from exc


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_api_audit(audit: Path, raw_dir: Path, suffix: str) -> dict[str, int]:
    referenced: set[Path] = set()
    successful = 0
    failed = 0
    events = 0
    for event in jsonl(audit):
        events += 1
        url = event.get("url")
        if not url:
            continue
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if event.get("query_sha256") != key:
            raise ValueError(f"query hash mismatch in {audit}: {key}")
        raw_hash = event.get("raw_sha256")
        if raw_hash:
            path = raw_dir / f"{key}.{suffix}"
            if not path.is_file() or sha256(path) != raw_hash:
                raise ValueError(f"raw response hash mismatch: {path}")
            referenced.add(path)
            successful += 1
        elif event.get("event") == "http_attempt":
            failed += 1
    raw_files = set(raw_dir.glob(f"*.{suffix}"))
    if raw_files != referenced:
        raise ValueError(f"unmatched raw responses in {raw_dir}: {len(raw_files ^ referenced)}")
    return {"audit_events": events, "with_verified_raw": successful,
            "failed_http_attempts": failed, "unique_raw_files": len(raw_files)}


def verify_conference_manifests() -> dict[str, int]:
    results: dict[str, int] = {}
    for source in ("ml", "nlp_vision"):
        raw_dir = ROOT / "conferences" / source / "raw"
        manifests = sorted(raw_dir.glob("*.manifest.json"))
        if not manifests:
            raise ValueError(f"missing conference source manifests: {raw_dir}")
        for manifest in manifests:
            item = json.loads(manifest.read_text(encoding="utf-8"))
            target = raw_dir / item["filename"]
            if not target.is_file() or sha256(target) != item["sha256"]:
                raise ValueError(f"conference raw hash mismatch: {target}")
            if target.stat().st_size != item["bytes"]:
                raise ValueError(f"conference raw byte count mismatch: {target}")
            if not item.get("source_url") or not item.get("fetched_at_utc"):
                raise ValueError(f"conference source provenance missing: {manifest}")
        results[source] = len(manifests)
    return results


def verify_monthly() -> dict[str, object]:
    result: dict[str, object] = {}
    for source, name, expected_metrics in (
        ("openalex", "openalex_monthly.csv", 3),
        ("arxiv", "arxiv_monthly.csv", 3),
    ):
        rows = csv_rows(ROOT / "data" / name)
        keys = [(row["month"], row["metric"]) for row in rows]
        months = sorted({row["month"] for row in rows})
        if len(keys) != len(set(keys)) or len(rows) != 81 * expected_metrics:
            raise ValueError(f"{source} main monthly grid is incomplete or duplicated")
        if len(months) != 81 or months[0] != "2020-01" or months[-1] != "2026-09":
            raise ValueError(f"{source} calendar range changed")
        if any(row["status"] != "ok" or row.get("count", "") == "" for row in rows):
            raise ValueError(f"{source} main monthly grid has a failed/missing cell")
        wide = csv_rows(ROOT / "data" / "processed" / f"{source}_monthly_wide.csv")
        if len(wide) != 81 or [row["month"] for row in wide] != months:
            raise ValueError(f"{source} derived monthly grid does not match source")
        result[source] = {"months": len(months), "main_queries_ok": len(rows)}
    pilot = csv_rows(ROOT / "data" / "arxiv_internal_pilot.csv")
    statuses = Counter(row["status"] for row in pilot)
    if len(pilot) != 18 or statuses != Counter({"ok": 10, "missing": 8}):
        raise ValueError(f"arXiv internal pilot status changed: {statuses}")
    if any(row.get("count") not in ("", None) for row in pilot if row["status"] == "missing"):
        raise ValueError("missing arXiv internal count was filled in")
    result["arxiv_internal_pilot"] = dict(statuses)
    return result


def verify_titles() -> dict[str, object]:
    counts = {}
    for source, name in (("ml", "metadata_main.jsonl"), ("nlp_vision", "papers_main.jsonl")):
        path = ROOT / "conferences" / source / name
        keys = set()
        count = 0
        for row in jsonl(path):
            count += 1
            key = (row["venue"], int(row["year"]), row["paper_id"])
            if key in keys:
                raise ValueError(f"duplicate venue-year title ID in {path}: {key}")
            keys.add(key)
        counts[source] = count
    if counts != {"ml": 57957, "nlp_vision": 25380}:
        raise ValueError(f"conference source count changed: {counts}")
    rule_hash = sha256(ROOT / "conferences" / "shared_title_rules.json")
    yearly = csv_rows(ROOT / "conferences" / "processed" / "shared_title_yearly.csv")
    if not yearly or any(row["rule_sha256"] != rule_hash for row in yearly):
        raise ValueError("conference title rule hash mismatch")
    return {"source_records": counts, "total_venue_year_records": sum(counts.values()),
            "title_rule_sha256": rule_hash, "yearly_rows": len(yearly)}


def verify_local_links() -> int:
    checked = 0
    for page in ROOT.rglob("*.md"):
        if "raw" in page.relative_to(ROOT).parts:
            continue
        for target in re.findall(r"\]\(([^)]+)\)", page.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (page.parent / target).resolve().exists():
                raise ValueError(f"broken local Markdown link in {page}: {target}")
            checked += 1
    return checked


def verify_sensitivity_samples() -> dict[str, object]:
    monthly = {row["month"]: int(row["ai_primary_1702_works"])
               for row in csv_rows(ROOT / "data/processed/openalex_monthly_wide.csv")}
    topics = csv_rows(ROOT / "data/openalex_ai_topics.csv")
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in topics:
        grouped.setdefault(row["month"], []).append(row)
    if len(grouped) != 45 or min(grouped) != "2023-01" or max(grouped) != "2026-09":
        raise ValueError("OpenAlex AI topic monthly window changed")
    for month, rows in grouped.items():
        expected = monthly[month]
        if sum(int(row["works"]) for row in rows) != expected or any(
                int(row["ai_primary_total"]) != expected for row in rows):
            raise ValueError(f"AI topic sum differs from main monthly total: {month}")
    metadata = csv_rows(ROOT / "data/openalex_metadata_sample.csv")
    screen = csv_rows(ROOT / "data/openalex_ai_sample_screen.csv")
    if len(metadata) != 180 or len(screen) != 60 or any(row["sample_seed"] != "20261009" for row in screen):
        raise ValueError("OpenAlex fixed-seed sample frame changed")
    screen_counts = Counter(row["screen"] for row in screen)
    if screen_counts["obvious_non_ai"] != 13:
        raise ValueError(f"OpenAlex conservative screen changed: {screen_counts}")
    acl = csv_rows(ROOT / "conferences/processed/acl_agent_abstract_reviewed.csv")
    acl_groups = Counter(row["candidate_group"] for row in acl)
    if len(acl) != 16 or sorted(acl_groups.values()) != [8, 8]:
        raise ValueError(f"ACL Agent directed abstract sample changed: {acl_groups}")
    return {"ai_topic_months_reconciled": len(grouped), "openalex_metadata_sample": len(metadata),
            "openalex_ai_screen": dict(screen_counts), "acl_agent_directed_review": dict(acl_groups),
            "label_provenance": "assistant title and available abstract review; not expert ground truth"}


def validate() -> dict[str, object]:
    result = {
        "status": "ok",
        "source_snapshot_utc": "2026-10-09",
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "api_audit": {
            "openalex": verify_api_audit(ROOT / "data" / "query_audit.jsonl",
                                          ROOT / "data" / "raw" / "openalex", "json"),
            "arxiv": verify_api_audit(ROOT / "data" / "arxiv_query_audit.jsonl",
                                       ROOT / "data" / "raw" / "arxiv", "xml"),
        },
        "conference_raw_manifests": verify_conference_manifests(),
        "monthly": verify_monthly(),
        "conference_titles": verify_titles(),
        "sensitivity_samples": verify_sensitivity_samples(),
        "local_markdown_links_checked": verify_local_links(),
        "published_outputs_sha256": {name: sha256(ROOT / name) for name in DETERMINISTIC_OUTPUTS},
    }
    return result


def rebuild(output_dir: Path) -> dict[str, object]:
    before = validate()
    destination = output_dir.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("rebuild output must not be inside research_trends")
    module = destination / "research_trends"
    if module.exists():
        raise ValueError(f"rebuild destination already exists: {module}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, module, ignore=shutil.ignore_patterns("__pycache__", "DELIVERY_IDS.json"))
    for name in DETERMINISTIC_OUTPUTS:
        (module / name).unlink()
    commands = (
        [sys.executable, str(module / "conferences/nlp_vision/normalize.py")],
        [sys.executable, str(module / "conferences/ml/normalize.py")],
        [sys.executable, str(module / "analyze_openalex.py"), "--data-dir", str(module / "data"),
         "--report", str(module / "reports/trends.html")],
        [sys.executable, str(module / "analyze_arxiv.py")],
        [sys.executable, str(module / "conferences/analyze_shared_titles.py")],
        [sys.executable, str(module / "build_dashboard.py")],
    )
    logs = destination / "rebuild_logs"
    logs.mkdir(exist_ok=True)
    for index, command in enumerate(commands, 1):
        process = subprocess.run(command, cwd=destination, capture_output=True, text=True)
        (logs / f"step_{index:02d}.stdout.log").write_text(process.stdout, encoding="utf-8")
        (logs / f"step_{index:02d}.stderr.log").write_text(process.stderr, encoding="utf-8")
        if process.returncode:
            raise RuntimeError(f"offline rebuild step {index} failed; see {logs}")
    actual = {name: sha256(module / name) for name in DETERMINISTIC_OUTPUTS}
    matches = {name: actual[name] == before["published_outputs_sha256"][name]
               for name in DETERMINISTIC_OUTPUTS}
    if not all(matches.values()):
        raise ValueError(f"rebuild differs from published deterministic outputs: "
                         f"{[name for name, ok in matches.items() if not ok]}")
    receipt = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ok", "network_calls": 0, "code_sha256": sha256(ROOT / "reproduce.py"),
        "input_snapshot": before, "commands": list(commands),
        "expected_sha256": before["published_outputs_sha256"],
        "actual_sha256": actual, "tolerance": "byte-identical SHA-256",
        "checks": matches, "logs": [f"rebuild_logs/step_{i:02d}.*.log" for i in range(1, len(commands) + 1)],
    }
    (destination / "rebuild_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    build = sub.add_parser("rebuild")
    build.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = validate() if args.command == "validate" else rebuild(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
