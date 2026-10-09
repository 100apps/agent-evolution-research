#!/usr/bin/env python3
"""Build a self-contained, offline conference catalog report from frozen sources."""

from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "research_trends/catalog/data/master_papers.csv.gz"
PATCH = ROOT / "research_trends/catalog/metadata_snapshot/metadata_patch.jsonl.gz"
RECEIPT = ROOT / "research_trends/catalog/data/master_receipt.json"
TAXONOMY = ROOT / "research_trends/catalog/taxonomy.json"
TEMPLATE = ROOT / "tools/monthly_catalog_template.html.in"
OUTPUT = ROOT / "reports/paper-monthly-analysis.html"
FIELDS = ("paper_id", "occurrence_id", "title", "official_url", "venue", "year", "real_month", "l1", "l2", "l3")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    master_sha = sha256(MASTER)
    if master_sha != receipt["gzip_sha256"]:
        raise SystemExit("主表 gzip SHA-256 与归档 receipt 不一致")

    real_months: dict[str, str] = {}
    with gzip.open(PATCH, "rt", encoding="utf-8") as stream:
        for line in stream:
            patch = json.loads(line)
            date = patch.get("publication_date") or ""
            if (
                patch.get("date_precision") in ("month", "day")
                and patch.get("date_type") == "proceedings_bibliographic_date"
                and len(date) >= 7
                and date[4] == "-"
            ):
                real_months[patch["occurrence_id"]] = date[:7]

    csv_buffer = io.StringIO(newline="")
    writer = csv.writer(csv_buffer, lineterminator="\n")
    writer.writerow(FIELDS)
    years: Counter[str] = Counter()
    venues: Counter[str] = Counter()
    real_count = 0
    rows = 0
    with gzip.open(MASTER, "rt", encoding="utf-8-sig", newline="") as stream:
        for paper in csv.DictReader(stream):
            occurrences = json.loads(paper["occurrences_json"])
            for occurrence in occurrences:
                oid = occurrence["occurrence_id"]
                venue = occurrence["venue"]
                year = str(occurrence["year"])
                real_month = real_months.get(oid, "")
                if real_month and not real_month.startswith(year + "-"):
                    raise SystemExit(f"书目月份与会议届次年不一致：{oid} {year} {real_month}")
                writer.writerow((
                    paper["paper_id"], oid, paper["title"], paper["official_url"], venue, year, real_month,
                    "|".join(json.loads(paper["category_ids_l1_json"])),
                    "|".join(json.loads(paper["category_ids_l2_json"])),
                    "|".join(json.loads(paper["category_ids_l3_json"])),
                ))
                rows += 1
                years[year] += 1
                venues[venue] += 1
                real_count += bool(real_month)
    if rows != receipt["rows"] or real_count != 25379:
        raise SystemExit(f"输入数量变化：rows={rows}, real_months={real_count}")

    csv_bytes = csv_buffer.getvalue().encode("utf-8")
    payload = base64.b64encode(gzip.compress(csv_bytes, compresslevel=9, mtime=0)).decode("ascii")
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    nodes = {node["id"]: {"name": node["label_zh"], "parent": node["parent_id"], "level": node["level"]} for node in taxonomy["nodes"]}
    meta = {
        "rows": rows,
        "real_month_rows": real_count,
        "virtual_month_rows": rows - real_count,
        "years": dict(sorted(years.items())),
        "venues": dict(sorted(venues.items())),
        "master_gzip_sha256": master_sha,
        "patch_gzip_sha256": sha256(PATCH),
        "projection_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "taxonomy_version": taxonomy["version"],
        "nodes": nodes,
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    html = template.replace("__REPORT_META__", json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__CSV_GZIP_BASE64__", payload)
    if "__REPORT_META__" in html or "__CSV_GZIP_BASE64__" in html:
        raise SystemExit("模板占位符未替换")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT), "rows": rows, "real_month_rows": real_count,
        "virtual_month_rows": rows - real_count, "years": meta["years"],
        "html_bytes": OUTPUT.stat().st_size, "html_sha256": sha256(OUTPUT),
        "source_sha256": master_sha, "projection_csv_sha256": meta["projection_csv_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
