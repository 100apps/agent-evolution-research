#!/usr/bin/env python3
"""Validate offline report structure, embedded panorama and relative links."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paper_cards = 0
        self.notes = 0
        self.experiments = 0
        self.hrefs: list[str] = []
        self.charset_utf8 = False
        self.panorama_embedded = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "article" and "paper" in classes:
            self.paper_cards += 1
        if tag == "details" and "note" in classes:
            self.notes += 1
        if tag in {"article", "div"} and "experiment" in classes:
            self.experiments += 1
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag == "meta" and (values.get("charset") or "").lower() == "utf-8":
            self.charset_utf8 = True
        if (
            tag == "img"
            and "39 篇论文全景图" in (values.get("alt") or "")
            and (values.get("src") or "").startswith("data:image/png;base64,")
        ):
            self.panorama_embedded = True


def validate(report: Path) -> dict:
    source = report.read_text(encoding="utf-8", errors="strict")
    parser = ReportParser()
    parser.feed(source)
    missing: list[str] = []
    checked: list[str] = []
    for href in parser.hrefs:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or href.startswith("#"):
            continue
        target = (report.parent / unquote(parsed.path)).resolve()
        checked.append(str(target))
        if not target.is_file():
            missing.append(href)
    checks = {
        "doctype": source.lstrip().lower().startswith("<!doctype html>"),
        "charset_utf8": parser.charset_utf8,
        "paper_cards_41": parser.paper_cards == 41,
        "research_notes_8": parser.notes == 8,
        "experiment_blocks_3": parser.experiments == 3,
        "panorama_embedded_data_uri": parser.panorama_embedded,
        "local_links_checked": len(checked),
        "missing_local_links": missing,
    }
    required = [
        "doctype",
        "charset_utf8",
        "paper_cards_41",
        "research_notes_8",
        "experiment_blocks_3",
        "panorama_embedded_data_uri",
    ]
    if not all(checks[key] for key in required) or missing:
        raise SystemExit(json.dumps(checks, ensure_ascii=False, indent=2))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "index.html")
    args = parser.parse_args()
    print(json.dumps(validate(args.report.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
