"""校验 PDF、计算哈希并逐页提取正文。

此脚本不访问网络，也不修改原始 PDF。输出位于 metadata/、text/ 和 logs/。
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PAPERS_DIR = ROOT / "papers"
TEXT_DIR = ROOT / "text"
METADATA_DIR = ROOT / "metadata"
LOGS_DIR = ROOT / "logs"
EXPECTED_CORE = 38
EXPECTED_SUPPLEMENTAL = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_metadata_value(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return repr(value)


def inspect_pdf(path: Path, group: str) -> dict[str, object]:
    relative = path.relative_to(ROOT).as_posix()
    record: dict[str, object] = {
        "group": group,
        "path": relative,
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "pdf_magic": False,
        "status": "pending",
        "pages": 0,
        "text_pages_nonempty": 0,
        "text_chars": 0,
        "encrypted": None,
        "title_metadata": None,
        "author_metadata": None,
        "errors": [],
    }

    with path.open("rb") as handle:
        record["pdf_magic"] = handle.read(5) == b"%PDF-"
    if not record["pdf_magic"]:
        record["status"] = "invalid_magic"
        record["errors"] = ["文件不是以 %PDF- 开头"]
        return record

    output_dir = TEXT_DIR / group
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{path.stem}.txt"

    try:
        reader = PdfReader(path, strict=False)
        record["encrypted"] = bool(reader.is_encrypted)
        if reader.is_encrypted:
            decrypt_result = reader.decrypt("")
            if not decrypt_result:
                record["status"] = "encrypted_unreadable"
                record["errors"] = ["PDF 已加密且空密码无法读取"]
                return record

        metadata = reader.metadata or {}
        record["title_metadata"] = normalize_metadata_value(metadata.get("/Title"))
        record["author_metadata"] = normalize_metadata_value(metadata.get("/Author"))
        record["pages"] = len(reader.pages)

        page_chunks: list[str] = []
        errors: list[str] = []
        nonempty = 0
        total_chars = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # 保留其余页并记录精确页码
                text = ""
                errors.append(f"page {page_number}: {type(exc).__name__}: {exc}")
            text = text.replace("\x00", "")
            # 部分论文的自定义数学字体会让 pypdf 返回孤立 UTF-16
            # surrogate；替换为 U+FFFD，避免整篇正文因单个坏字形写入失败。
            text = text.encode("utf-8", errors="replace").decode("utf-8")
            if text.strip():
                nonempty += 1
            total_chars += len(text)
            page_chunks.append(f"\n\n===== PAGE {page_number} / {len(reader.pages)} =====\n\n{text}")

        output_path.write_text("".join(page_chunks).lstrip(), encoding="utf-8")
        record["text_path"] = output_path.relative_to(ROOT).as_posix()
        record["text_pages_nonempty"] = nonempty
        record["text_chars"] = total_chars
        record["errors"] = errors
        if errors:
            record["status"] = "partial_text_extraction"
        elif nonempty == 0:
            record["status"] = "no_extractable_text"
        else:
            record["status"] = "ok"
    except Exception as exc:
        record["status"] = "read_error"
        record["errors"] = [f"{type(exc).__name__}: {exc}"]
        record["traceback"] = traceback.format_exc()
    return record


def main() -> int:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    core_files = sorted(PAPERS_DIR.glob("*.pdf"))
    supplemental_files = sorted((PAPERS_DIR / "supplemental").glob("*.pdf"))
    started_at = datetime.now(timezone.utc)

    records = [inspect_pdf(path, "core") for path in core_files]
    records.extend(inspect_pdf(path, "supplemental") for path in supplemental_files)

    counts: dict[str, int] = {}
    for record in records:
        status = str(record["status"])
        counts[status] = counts.get(status, 0) + 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "expected_core": EXPECTED_CORE,
        "actual_core": len(core_files),
        "expected_supplemental": EXPECTED_SUPPLEMENTAL,
        "actual_supplemental": len(supplemental_files),
        "status_counts": counts,
        "records": records,
    }
    (METADATA_DIR / "pdf_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    csv_fields = [
        "group",
        "filename",
        "status",
        "bytes",
        "sha256",
        "pdf_magic",
        "pages",
        "text_pages_nonempty",
        "text_chars",
        "encrypted",
        "title_metadata",
        "author_metadata",
        "text_path",
        "errors",
    ]
    with (METADATA_DIR / "pdf_manifest.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["errors"] = " | ".join(record.get("errors", []))
            writer.writerow(row)

    duration = (datetime.now(timezone.utc) - started_at).total_seconds()
    log_lines = [
        f"generated_at={manifest['generated_at']}",
        f"duration_seconds={duration:.3f}",
        f"core={len(core_files)}/{EXPECTED_CORE}",
        f"supplemental={len(supplemental_files)}/{EXPECTED_SUPPLEMENTAL}",
        f"status_counts={json.dumps(counts, ensure_ascii=False, sort_keys=True)}",
    ]
    for record in records:
        log_lines.append(
            "\t".join(
                [
                    str(record["status"]),
                    str(record["pages"]),
                    str(record["text_chars"]),
                    str(record["sha256"]),
                    str(record["path"]),
                ]
            )
        )
    (LOGS_DIR / "extraction.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    expected_counts_ok = (
        len(core_files) == EXPECTED_CORE
        and len(supplemental_files) == EXPECTED_SUPPLEMENTAL
    )
    failures = [record for record in records if record["status"] != "ok"]
    print(json.dumps({"expected_counts_ok": expected_counts_ok, "status_counts": counts}, ensure_ascii=False))
    return 0 if expected_counts_ok and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
