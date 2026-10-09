"""Package this research module, including raw evidence, for offline transfer."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "agent-evolution-trends-data-code-20261009.zip"
EXCLUDE_DIRS = {"_library_helper_20261009", "__pycache__"}


def main() -> None:
    files = sorted(
        path for path in ROOT.rglob("*")
        if path.is_file() and not set(path.relative_to(ROOT).parts) & EXCLUDE_DIRS
    )
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, "research_trends/" + path.relative_to(ROOT).as_posix())
    with ZipFile(OUTPUT) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failed: {bad}")
    print(f"{OUTPUT}\nfiles={len(files)}\nbytes={OUTPUT.stat().st_size}")


if __name__ == "__main__":
    main()
