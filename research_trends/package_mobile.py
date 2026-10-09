"""Create independently extractable, source-grouped ZIPs below 20 MB each."""

from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "mobile_packages"
LIMIT = 19_000_000
CORPORA = {
    "conferences/ml/metadata_main.jsonl",
    "conferences/ml/metadata_main.csv",
    "conferences/nlp_vision/papers_main.jsonl",
    "conferences/nlp_vision/papers_main.csv",
    "conferences/processed/shared_title_assignments.csv",
}
EXCLUDED = {"DELIVERY_IDS.json"}
README = (
    "Each ZIP is an independent archive. Extract all selected archives into "
    "one directory to reconstruct research_trends/. No binary split parts.\n"
    "Data sources, query hashes, caveats, and rerun commands are in "
    "research_trends/README.md and report_zh.md.\n"
)


def group_for(relative: str) -> str:
    if relative in CORPORA:
        return "normalized-corpora"
    if relative.startswith("data/raw/openalex/"):
        return "openalex-raw"
    if relative.startswith("data/raw/arxiv/"):
        return "arxiv-raw"
    if relative.startswith("conferences/ml/raw/"):
        return "ml-raw"
    if relative.startswith("conferences/nlp_vision/raw/"):
        return "nlp-vision-raw"
    return "code-aggregates"


def write_zip(path: Path, files: list[Path]) -> int:
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("README_MOBILE_PACKAGES.txt", README)
        for file in files:
            archive.write(file, "research_trends/" + file.relative_to(ROOT).as_posix())
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"CRC error in {path.name}: {bad}")
    return path.stat().st_size


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    groups: dict[str, list[Path]] = {}
    for file in sorted(ROOT.rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(ROOT).as_posix()
        if (
            relative in EXCLUDED
            or file.suffix in {".pyc", ".pyo"}
            or "__pycache__" in file.parts
            or any(part.startswith("_") and part.endswith("helper") for part in file.relative_to(ROOT).parts)
        ):
            continue
        groups.setdefault(group_for(relative), []).append(file)

    manifest: list[dict[str, object]] = []

    def pack(group: str, files: list[Path], ordinal: str) -> None:
        path = OUTPUT / f"trends-{group}-{ordinal}.zip"
        size = write_zip(path, files)
        if size > LIMIT:
            path.unlink()
            if len(files) < 2:
                raise RuntimeError(f"Single file cannot fit below {LIMIT}: {files[0]}")
            total = sum(file.stat().st_size for file in files)
            cumulative = 0
            split = 1
            for i, file in enumerate(files[:-1], 1):
                cumulative += file.stat().st_size
                if cumulative >= total / 2:
                    split = i
                    break
            pack(group, files[:split], ordinal + "a")
            pack(group, files[split:], ordinal + "b")
            return
        manifest.append({
            "file": path.name,
            "group": group,
            "bytes": size,
            "sha256": digest(path),
            "source_files": len(files),
        })

    for group, files in sorted(groups.items()):
        pack(group, files, "01")
    manifest.sort(key=lambda row: str(row["file"]))
    expected = {
        "research_trends/" + file.relative_to(ROOT).as_posix()
        for files in groups.values() for file in files
    }
    archived: list[str] = []
    for row in manifest:
        with ZipFile(OUTPUT / str(row["file"])) as archive:
            archived.extend(name for name in archive.namelist() if name != "README_MOBILE_PACKAGES.txt")
    if len(archived) != len(set(archived)) or set(archived) != expected:
        raise RuntimeError("Mobile archives have missing or duplicate source files")
    (OUTPUT / "mobile_zip_manifest.json").write_text(
        json.dumps({"size_limit_bytes": LIMIT, "archives": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
