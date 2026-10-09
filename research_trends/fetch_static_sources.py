#!/usr/bin/env python3
"""Download a bounded set of public primary-source tables with hash verification."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCES = {
    "stanford_private_ai_2026.csv": (
        "https://drive.google.com/uc?export=download&id=1nIbhiNMDIulmGzgyeSKrqB7eLCcXBj4y",
        "c0f3254e3f6be162f51e53eddb48ffcf827990aa6a334de0eeaf844e73a7921b"),
    "stanford_private_genai_2026.csv": (
        "https://drive.google.com/uc?export=download&id=1RY99SZ8sKL4hcxxqnhrQNowxhRnghMrX",
        "a9843435810b0bf8b314591c033c4c256991e5865f9da5af9bceda583a16e285"),
    "stanford_github_ai_projects_2026.csv": (
        "https://drive.google.com/uc?export=download&id=11OeeK6mJ0xgpY8QvnXRqGQwJ949wCG2e",
        "b9bfe02f0014f8636c0481659eefedc96104904ecf3e2ac9cd0b31906d07eb96"),
    "github_topics_2026-05.csv": (
        "https://raw.githubusercontent.com/github/innovationgraph/078fb62ee4395d321bec9f4f06694cca68f6b6cb/data/topics.csv",
        "cb9602d0a63a1fa9bc0b54cf6b605fbf670dd181eee4e0b3480f7bae6552e3cd"),
    "epoch_notable_models_2026-10.csv": (
        "https://epoch.ai/data/notable_ai_models.csv",
        "bacde4f9af388703ceebd01cf71a14854f93b8995e425141b016e48f21d4e7df"),
    "nsf_doctorates_2025.xlsx": (
        "https://www.ncses.nsf.gov/pubs/nsf26326/assets/data-tables/tables/nsf26326-tab003-001.xlsx", None),
    "oecd_ai_hiring_2026.xlsx": (
        "https://stat.link/files/7e710f54-en/ls1u0b.xlsx", None),
}


def main():
    root = Path("research_trends/data/raw/static")
    root.mkdir(parents=True, exist_ok=True)
    audit = []
    for name, (url, expected_sha) in SOURCES.items():
        target = root / name
        if target.exists():
            raw = target.read_bytes()
            status = "cache_hit"
            http_status = None
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "agent-evolution-research-trends/0.1"})
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    raw = response.read(25_000_001)
                    http_status = response.status
                    content_type = response.headers.get("Content-Type")
                if len(raw) > 25_000_000:
                    status = "too_large_not_saved"
                elif raw.lstrip().lower().startswith(b"<!doctype html") or raw.lstrip().lower().startswith(b"<html"):
                    status = "html_not_source_data"
                else:
                    target.write_bytes(raw)
                    status = "downloaded"
            except (urllib.error.URLError, TimeoutError) as exc:
                raw, http_status, content_type, status = b"", None, None, "missing"
                error = repr(exc)
        observed = hashlib.sha256(raw).hexdigest() if raw else None
        record = {"name": name, "url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                  "status": status, "http_status": http_status, "bytes": len(raw), "sha256": observed,
                  "expected_sha256_from_independent_audit": expected_sha,
                  "hash_matches_independent_audit": observed == expected_sha if expected_sha else None}
        if status == "downloaded":
            record["content_type"] = content_type
        if status == "missing":
            record["error"] = error
        audit.append(record)
        time.sleep(1)
    (root / "download_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"downloaded_or_cached": sum(r["status"] in ("downloaded", "cache_hit") for r in audit),
                      "hash_matches": sum(r["hash_matches_independent_audit"] is True for r in audit),
                      "missing_or_invalid": sum(r["status"] not in ("downloaded", "cache_hit") for r in audit)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
