#!/usr/bin/env python3
"""Single safe entry point for validation, tests, experiments and report build."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ("acrouter_replay", "evoc2f_scheduler", "validation_bias")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"invalid PNG: {path}")
    return (int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big"))


def validate_repository() -> dict:
    manifest = load(ROOT / "metadata" / "pdf_manifest.json")
    registry = load(ROOT / "metadata" / "paper_registry.json")
    topic_map = load(ROOT / "metadata" / "agent_evolution_map.json")
    errors: list[str] = []

    if len(manifest["records"]) != 39 or manifest["status_counts"] != {"ok": 39}:
        errors.append("PDF manifest is not 39/39 ok")
    for record in manifest["records"]:
        path = ROOT / record["path"]
        if not path.is_file():
            errors.append(f"missing PDF: {record['path']}")
        elif sha256(path) != record["sha256"]:
            errors.append(f"PDF hash mismatch: {record['path']}")

    paper_ids = [paper["paper_id"] for paper in registry["papers"]]
    if registry.get("count") != 39 or len(paper_ids) != len(set(paper_ids)):
        errors.append("paper registry does not contain 39 unique paper_id values")
    for paper in registry["papers"]:
        for field in ("local_pdf", "local_text", "analysis_file"):
            if not (ROOT / paper[field]).is_file():
                errors.append(f"registry missing {field}: {paper[field]}")
        if (ROOT / paper["local_pdf"]).is_file() and sha256(ROOT / paper["local_pdf"]) != paper["pdf_sha256"]:
            errors.append(f"registry PDF hash mismatch: {paper['paper_id']}")

    map_papers = [paper for group in topic_map["groups"] for paper in group["papers"]]
    map_keys = [str(paper["inventory_index"]) for paper in map_papers]
    if topic_map.get("count") != 39 or len(map_keys) != 39 or len(set(map_keys)) != 39:
        errors.append("topic map does not contain 39 unique entries")

    image = ROOT / "assets" / "Agent_自进化论文全景图.png"
    if not image.is_file():
        errors.append("panorama image missing")
        image_size = None
    else:
        image_size = png_size(image)
        if image_size != (3600, 3320):
            errors.append(f"panorama dimensions differ: {image_size}")

    oversize = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and path.stat().st_size >= 100_000_000
    ]
    if oversize:
        errors.append("files reach GitHub 100 MB limit: " + ", ".join(oversize))

    excluded_parts = {"papers", "text", "tmp", ".git", "run_outputs"}
    personal_patterns = [
        re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\", re.IGNORECASE),
        re.compile("/workspace/" + "shared/"),
    ]
    secret_patterns = [
        re.compile(r"gh[opsu]_[A-Za-z0-9]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    scanned = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or excluded_parts.intersection(path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() not in {".md", ".py", ".json", ".csv", ".log", ".txt", ".html"}:
            continue
        if path == ROOT / "reports" / "index.html":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        normalized_text = text.replace("\\\\", "\\")
        scanned += 1
        for pattern in personal_patterns:
            if pattern.search(normalized_text):
                errors.append(f"personal absolute path in {path.relative_to(ROOT).as_posix()}")
        for pattern in secret_patterns:
            if pattern.search(text):
                errors.append(f"possible credential in {path.relative_to(ROOT).as_posix()}")

    result = {
        "pdfs_verified": len(manifest["records"]),
        "registry_papers": len(registry["papers"]),
        "topic_map_papers": len(map_papers),
        "panorama_size": image_size,
        "oversize_files": oversize,
        "text_files_privacy_scanned": scanned,
        "errors": sorted(set(errors)),
    }
    if result["errors"]:
        raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def run_logged(command: list[str], log_dir: Path) -> subprocess.CompletedProcess[str]:
    log_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    (log_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
    (log_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
    (log_dir / "run.log").write_text(
        "$ " + " ".join(command[:2] + ["--output-dir", "<OUTPUT_DIR>"]) + "\n"
        + result.stdout
        + ("\n[stderr]\n" + result.stderr if result.stderr else ""),
        encoding="utf-8",
    )
    if result.returncode:
        raise SystemExit(f"command failed ({result.returncode}); see {log_dir / 'stderr.log'}")
    return result


def run_tests(output_dir: Path | None = None) -> dict:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "tests.stdout.log").write_text(result.stdout, encoding="utf-8")
        (output_dir / "tests.stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    return {"tests": "passed", "command": "python -m unittest discover -s tests -v"}


def run_experiments(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for name in EXPERIMENTS:
        target = output_dir / name
        command = [
            sys.executable,
            str(ROOT / "experiments" / name / "run.py"),
            "--output-dir",
            str(target),
        ]
        run_logged(command, target)
        committed = load(ROOT / "experiments" / name / "experiment_manifest.json")
        actual = load(target / "results.json")
        receipt = {
            "schema_version": 1,
            "experiment": name,
            "command": f"python experiments/{name}/run.py --output-dir <OUTPUT_DIR>",
            "repository_commit": git_commit(),
            "code_sha256": sha256(ROOT / "experiments" / name / "run.py"),
            "input_files": committed["input_files"],
            "configuration": committed["configuration"],
            "seed": committed["seed"],
            "determinism": committed["determinism"],
            "environment": {
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": platform.platform(),
            },
            "expected": committed["expected"],
            "actual": actual,
            "tolerance": committed["tolerance"],
            "returncode": 0,
            "complete_output": ["stdout.log", "stderr.log", "run.log", "results.json"],
        }
        (target / "run_receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        summaries[name] = {
            "evidence_level": committed["evidence_level"],
            "results_sha256": sha256(target / "results.json"),
            "checks": actual.get("checks", actual.get("reference_checks")),
        }
    return summaries


def build_report(output_dir: Path, experiment_root: Path | None = None) -> dict:
    report_path = output_dir / "reports" / "index.html"
    analysis_path = output_dir / "metadata" / "paper_analysis.json"
    experiment_root = experiment_root or (ROOT / "experiments")
    command = [
        sys.executable,
        str(ROOT / "tools" / "build_report.py"),
        "--output",
        str(report_path),
        "--experiment-root",
        str(experiment_root),
        "--analysis-output",
        str(analysis_path),
    ]
    result = run_logged(command, output_dir / "build")
    validation = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_report.py"), "--report", str(report_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    (output_dir / "build" / "validate_report.log").write_text(
        validation.stdout + validation.stderr, encoding="utf-8"
    )
    if validation.returncode:
        raise SystemExit(validation.stdout + validation.stderr)
    return {
        "report": str(report_path),
        "sha256": sha256(report_path),
        "build_stdout": result.stdout.strip(),
        "validation": json.loads(validation.stdout),
    }


def safe_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == ROOT:
        raise SystemExit("--output-dir must not be the repository root")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("test")
    sub.add_parser("trends-validate")
    trends_rebuild = sub.add_parser("trends-rebuild")
    trends_rebuild.add_argument("--output-dir", type=Path, required=True)
    for name in ("experiment", "build", "all"):
        command = sub.add_parser(name)
        command.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command in {"trends-validate", "trends-rebuild"}:
        command = [sys.executable, str(ROOT / "research_trends" / "reproduce.py")]
        command.append("validate" if args.command == "trends-validate" else "rebuild")
        if args.command == "trends-rebuild":
            command.extend(("--output-dir", str(safe_output(args.output_dir))))
        process = subprocess.run(command, cwd=ROOT)
        raise SystemExit(process.returncode)

    if args.command == "validate":
        print(json.dumps(validate_repository(), ensure_ascii=False, indent=2))
        return
    if args.command == "test":
        print(json.dumps(run_tests(), ensure_ascii=False, indent=2))
        return

    output_dir = safe_output(args.output_dir)
    if args.command == "experiment":
        result = run_experiments(output_dir / "experiments")
    elif args.command == "build":
        result = build_report(output_dir)
    else:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repository_commit": git_commit(),
            "validate": validate_repository(),
            "test": run_tests(output_dir / "test"),
        }
        result["experiments"] = run_experiments(output_dir / "experiments")
        result["build"] = build_report(output_dir, output_dir / "experiments")
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
