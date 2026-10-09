#!/usr/bin/env python3
"""Parse official ML proceedings/program catalogues to a title-only comparable table."""

from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

ROOT = Path(__file__).parent
RAW = ROOT / "raw"
PMLR = {2020: 119, 2021: 139, 2022: 162, 2023: 202, 2024: 235, 2025: 267, 2026: 306}


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text or ""))).strip()


def norm(text):
    return re.sub(r"[^\w]+", "", unicodedata.normalize("NFKC", text).casefold())


def source(name):
    record = json.loads((RAW / (name + ".manifest.json")).read_text(encoding="utf-8"))
    if not record.get("sha256"):
        raise ValueError(f"missing source {name}")
    return record


def openreview_id(url):
    if not url or "openreview.net/" not in url:
        return ""
    return (parse_qs(urlparse(url).query).get("id") or [""])[0]


def program_paper_id(paper):
    links = [paper.get("paper_url"), paper.get("paper_pdf_url")]
    links.extend(media.get("uri") for media in paper.get("eventmedia", []))
    return next((pid for link in links if (pid := openreview_id(link))), "")


def program_records(name):
    obj = json.loads((RAW / name).read_text(encoding="utf-8"))
    if obj.get("next") is not None or obj.get("count") != len(obj.get("results", [])):
        raise ValueError(f"program response incomplete: {name}")
    return obj["results"]


def basic(venue, year, paper_id, title, url, raw_name, source_type, track="main", abstract=""):
    item = source(raw_name)
    return {"paper_id": paper_id, "venue": venue, "year": year,
            "track": track, "title": clean(title), "abstract": clean(abstract), "official_url": url,
            "source_type": source_type, "source_url": item["source_url"],
            "source_sha256": item["sha256"], "source_fetched_at_utc": item["fetched_at_utc"]}


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows, excluded, coverage, duplicate_program_events = [], [], [], []
    for year, volume in PMLR.items():
        raw_name = f"icml_{year}.html"
        markup = (RAW / raw_name).read_text(encoding="utf-8")
        blocks = re.findall(r'<div class="paper">(.*?)</div>', markup, flags=re.S)
        position_titles = set()
        if year >= 2024:
            program_name = f"icml_{year}_program.json"
            for item in program_records(program_name):
                if item.get("eventtype") == "Poster" and "Position_Paper_Track" in (item.get("sourceurl") or ""):
                    position_titles.add(norm(item.get("name") or ""))
        selected = 0
        for block in blocks:
            title_match = re.search(r'<p class="title">(.*?)</p>', block, flags=re.S)
            link_match = re.search(r'<a href="([^"]+)">abs</a>', block)
            if not title_match or not link_match:
                raise ValueError(f"unparsed PMLR block {year}")
            title, url = clean(title_match.group(1)), html.unescape(link_match.group(1))
            position = (year >= 2024 and (norm(title) in position_titles or
                                             bool(re.match(r"^Position\s*:", title, re.I))))
            paper_id = f"pmlr:v{volume}:{urlparse(url).path.rsplit('/', 1)[-1].removesuffix('.html')}"
            record = basic("ICML", year, paper_id, title, url, raw_name,
                           "published_main_proceedings" if not position else "excluded_position_track",
                           "position" if position else "main")
            (excluded if position else rows).append(record)
            selected += not position
        coverage.append({"venue": "ICML", "year": year, "raw_records": len(blocks),
                         "main_unique": selected, "excluded_position": len(blocks)-selected,
                         "source_files": [raw_name], "source_type": "published_proceedings",
                         "warning": "position tracks excluded by official program titles and published Position: prefix"})
    for year in range(2020, 2026):
        raw_name = f"neurips_{year}.html"
        markup = (RAW / raw_name).read_text(encoding="utf-8")
        candidates = re.findall(r'<li class="([^"]*)"[^>]*>(.*?)</li>', markup, flags=re.S)
        selected = 0
        track_counts = {}
        for track_class, block in candidates:
            title_match = re.search(r'<a title="paper title" href="([^"]+)">(.*?)</a>', block, flags=re.S)
            if not title_match:
                continue
            path, title = title_match.groups()
            url = urljoin("https://papers.nips.cc", path)
            pid_match = re.search(r"/hash/([^-]+)-", path)
            if not pid_match:
                raise ValueError(f"missing NeurIPS hash: {url}")
            track = track_class or "main"
            included = track in ("main", "conference")
            track_counts[track] = track_counts.get(track, 0) + 1
            record = basic("NeurIPS", year, f"neurips:{year}:{pid_match.group(1)}", title,
                           url, raw_name, "published_main_proceedings" if included else "excluded_other_track", track)
            (rows if included else excluded).append(record)
            selected += included
        coverage.append({"venue": "NeurIPS", "year": year, "raw_records": sum(track_counts.values()),
                         "main_unique": selected, "excluded_tracks": track_counts,
                         "source_files": [raw_name], "source_type": "published_proceedings",
                         "warning": "official proceedings list-item classes used to exclude non-main tracks"})
    raw_name = "iclr_2020.json"
    data = json.loads((RAW / raw_name).read_text(encoding="utf-8"))
    for paper in data:
        content = paper["content"]
        pid = paper["forum"]
        rows.append(basic("ICLR", 2020, "openreview:" + pid, content["title"],
                          "https://openreview.net/forum?id=" + pid, raw_name,
                          "accepted_main_program", abstract=content.get("abstract", "")))
    coverage.append({"venue": "ICLR", "year": 2020, "raw_records": len(data), "main_unique": len(data),
                     "source_files": [raw_name], "source_type": "accepted_main_program",
                     "warning": "official virtual catalogue; abstract completeness must be checked"})
    for venue, years in (("ICLR", range(2021, 2027)), ("NeurIPS", (2026,))):
        for year in years:
            prefix = venue.lower()
            raw_name = f"{prefix}_{year}.json" if venue == "ICLR" else "neurips_2026_program.json"
            all_items = program_records(raw_name)
            posters = [paper for paper in all_items if paper.get("eventtype") == "Poster"]
            main = [paper for paper in posters if (year == 2021 and venue == "ICLR") or
                    paper.get("sourceurl") == f"https://openreview.net/group?id={venue}.cc/{year}/Conference"]
            unique = {}
            for paper in main:
                pid = program_paper_id(paper)
                key = "openreview:" + pid if pid else f"event:{prefix}:{paper['id']}"
                if key in unique:
                    duplicate_program_events.append({"venue": venue, "year": year, "paper_id": key,
                                                     "duplicate_event_id": paper["id"]})
                    continue
                unique[key] = paper
            for key, paper in unique.items():
                pid = program_paper_id(paper)
                url = ("https://openreview.net/forum?id=" + pid if pid else
                       urljoin(f"https://{prefix}.cc", paper.get("virtualsite_url") or f"/virtual/{year}/poster/{paper['id']}"))
                rows.append(basic(venue, year, key, paper["name"], url, raw_name,
                                  "provisional_program_incomplete" if venue == "NeurIPS" else "accepted_main_program",
                                  abstract=paper.get("abstract") or ""))
            coverage.append({"venue": venue, "year": year, "raw_records": len(all_items),
                             "poster_rows": len(posters), "main_poster_rows": len(main), "main_unique": len(unique),
                             "duplicate_main_events": len(main)-len(unique),
                             "source_files": [raw_name],
                             "source_type": "provisional_program_incomplete" if venue == "NeurIPS" else "accepted_main_program",
                             "warning": "2026 NeurIPS program not final; do not compare as complete edition" if venue == "NeurIPS" else
                                        "official accepted main-program catalogue, not initial decisions"})
    if any(not row["title"] or not row["paper_id"] for row in rows):
        raise ValueError("empty main title or ID")
    if len(rows) != len({(row["venue"], row["year"], row["paper_id"]) for row in rows}):
        raise ValueError("duplicate venue-year main paper ID")
    rows.sort(key=lambda row: (row["venue"], row["year"], row["paper_id"]))
    (ROOT / "metadata_main.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (ROOT / "metadata_excluded_tracks.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in excluded), encoding="utf-8")
    save_csv(ROOT / "metadata_main.csv", rows)
    (ROOT / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "duplicate_program_events.json").write_text(json.dumps(duplicate_program_events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "coverage": coverage}, ensure_ascii=False))


if __name__ == "__main__":
    main()
