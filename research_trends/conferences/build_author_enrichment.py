#!/usr/bin/env python3
"""Extract paper authors from saved official catalogues without network access.

Names and affiliations are copied only when the snapshot explicitly supplies them.
Country is never inferred from a name or institution string.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import html
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlparse


ROOT = Path(__file__).resolve().parent
ML = ROOT / "ml/raw"
NLP = ROOT / "nlp_vision/raw"
PMLR = {2020: 119, 2021: 139, 2022: 162, 2023: 202, 2024: 235, 2025: 267, 2026: 306}
FIELDS = ("venue", "year", "paper_id", "authors", "author_count", "affiliations",
          "affiliation_basis", "profile_institutions", "affiliation_countries", "country_basis",
          "authorships_json", "author_source_file", "author_source_sha256")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value or ""))).strip()


def put(index: dict, venue: str, year: int, paper_id: str, people: list[dict], raw_name: str,
        raw_dir: Path) -> None:
    people = [{key: str(value).strip() for key, value in person.items() if value}
              for person in people if person.get("name")]
    if not people:
        return
    key = (venue, year, paper_id)
    names = [person["name"] for person in people]
    affiliations = list(dict.fromkeys(person["affiliation"] for person in people if person.get("affiliation")))
    profiles = list(dict.fromkeys(person["profile_institution"] for person in people
                                  if person.get("profile_institution")))
    countries = list(dict.fromkeys(person["affiliation_country"] for person in people
                                   if person.get("affiliation_country")))
    manifest = json.loads((raw_dir / (raw_name + ".manifest.json")).read_text(encoding="utf-8"))
    row = dict(venue=venue, year=year, paper_id=paper_id, authors="; ".join(names),
               author_count=len(names), affiliations="; ".join(affiliations),
               affiliation_basis="paper_byline_xml" if affiliations else "",
               profile_institutions="; ".join(profiles),
               affiliation_countries="; ".join(countries),
               country_basis="explicit_author_country_field" if countries else "",
               authorships_json=json.dumps(people, ensure_ascii=False, separators=(",", ":")),
               author_source_file=f"{raw_dir.relative_to(ROOT).as_posix()}/{raw_name}",
               author_source_sha256=manifest["sha256"])
    old = index.get(key)
    if old and old["authors"] != row["authors"]:
        raise ValueError(f"conflicting author lists in official snapshots: {key}")
    index.setdefault(key, row)


def openreview_id(url: str) -> str:
    return (parse_qs(urlparse(url).query).get("id") or [""])[0] if url and "openreview.net/" in url else ""


def program_paper_id(paper: dict) -> str:
    links = [paper.get("paper_url"), paper.get("paper_pdf_url")]
    links.extend(media.get("uri") for media in paper.get("eventmedia", []))
    return next((pid for link in links if (pid := openreview_id(link))), "")


def collect_acl(index: dict) -> None:
    import xml.etree.ElementTree as ET

    for year in range(2020, 2027):
        raw_name = f"acl_{year}.xml"
        root = ET.parse(NLP / raw_name).getroot()
        for volume in root.findall("volume"):
            if volume.attrib.get("id") not in {"main", "long", "short"}:
                continue
            track = volume.attrib["id"]
            for paper in volume.findall("paper"):
                people = []
                for author in paper.findall("author"):
                    name = clean(" ".join((author.findtext("first") or "", author.findtext("last") or "")))
                    people.append({"name": name, "affiliation": clean(author.findtext("affiliation") or ""),
                                   "affiliation_country": clean(author.findtext("country") or ""),
                                   "author_id": author.attrib.get("id", ""),
                                   "orcid": author.attrib.get("orcid", "")})
                put(index, "ACL", year, f"{root.attrib['id']}-{track}.{paper.attrib['id']}",
                    people, raw_name, NLP)


def collect_cvpr(index: dict) -> None:
    for year in range(2020, 2027):
        names = ([f"cvpr_2020_day{day}.html" for day in (16, 17, 18)] if year == 2020
                 else [f"cvpr_{year}.html"])
        for raw_name in names:
            markup = (NLP / raw_name).read_text(encoding="utf-8")
            for title_block, detail_block in re.findall(
                    r'(<dt class="ptitle".*?</dt>)\s*<dd>(.*?)</dd>', markup, re.S):
                link = re.search(r'<a href="([^"]+)"', title_block)
                if not link:
                    continue
                url = urljoin("https://openaccess.thecvf.com/", html.unescape(link.group(1)))
                paper_id = "CVF:" + url.split(".com/", 1)[1]
                authors = [clean(value) for value in re.findall(
                    r'name="(?:query_author|query)"\s+value="([^"]+)"', detail_block)]
                put(index, "CVPR", year, paper_id, [{"name": name} for name in authors], raw_name, NLP)


def collect_icml(index: dict) -> None:
    for year, volume in PMLR.items():
        raw_name = f"icml_{year}.html"
        markup = (ML / raw_name).read_text(encoding="utf-8")
        for block in re.findall(r'<div class="paper">(.*?)</div>', markup, re.S):
            link = re.search(r'<a href="([^"]+)">abs</a>', block)
            authors = re.search(r'<span class="authors">(.*?)</span>', block, re.S)
            if not link or not authors:
                continue
            url = html.unescape(link.group(1))
            paper_id = f"pmlr:v{volume}:{urlparse(url).path.rsplit('/', 1)[-1].removesuffix('.html')}"
            people = [{"name": clean(name)} for name in clean(authors.group(1)).split(",")]
            put(index, "ICML", year, paper_id, people, raw_name, ML)


def collect_neurips(index: dict) -> None:
    for year in range(2020, 2026):
        raw_name = f"neurips_{year}.html"
        markup = (ML / raw_name).read_text(encoding="utf-8")
        for _, block in re.findall(r'<li class="([^"]*)"[^>]*>(.*?)</li>', markup, re.S):
            link = re.search(r'<a title="paper title" href="([^"]+)">', block)
            authors = re.search(r'<span class="paper-authors">(.*?)</span>', block, re.S)
            if not link or not authors:
                continue
            paper_hash = re.search(r"/hash/([^-]+)-", link.group(1))
            if not paper_hash:
                continue
            people = [{"name": clean(name)} for name in clean(authors.group(1)).split(",")]
            put(index, "NeurIPS", year, f"neurips:{year}:{paper_hash.group(1)}", people, raw_name, ML)
    raw_name = "neurips_2026_program.json"
    data = json.loads((ML / raw_name).read_text(encoding="utf-8"))
    for paper in data["results"]:
        if paper.get("eventtype") != "Poster":
            continue
        pid = program_paper_id(paper)
        key = "openreview:" + pid if pid else f"event:neurips:{paper['id']}"
        people = [{"name": person.get("fullname", ""),
                   "profile_institution": person.get("institution", "")}
                  for person in paper.get("authors", [])]
        put(index, "NeurIPS", 2026, key, people, raw_name, ML)


def collect_iclr(index: dict) -> None:
    raw_name = "iclr_2020.json"
    for paper in json.loads((ML / raw_name).read_text(encoding="utf-8")):
        people = [{"name": name} for name in paper.get("content", {}).get("authors", [])]
        put(index, "ICLR", 2020, "openreview:" + paper["forum"], people, raw_name, ML)
    for year in range(2021, 2027):
        raw_name = f"iclr_{year}.json"
        data = json.loads((ML / raw_name).read_text(encoding="utf-8"))
        for paper in data["results"]:
            if paper.get("eventtype") != "Poster":
                continue
            pid = program_paper_id(paper)
            key = "openreview:" + pid if pid else f"event:iclr:{paper['id']}"
            people = [{"name": person.get("fullname", ""),
                       "profile_institution": person.get("institution", "")}
                      for person in paper.get("authors", [])]
            put(index, "ICLR", year, key, people, raw_name, ML)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index: dict[tuple[str, int, str], dict] = {}
    for collect in (collect_acl, collect_cvpr, collect_icml, collect_neurips, collect_iclr):
        collect(index)
    base_ids = set()
    for source in (ROOT / "ml/metadata_main.jsonl", ROOT / "nlp_vision/papers_main.jsonl"):
        with source.open(encoding="utf-8") as stream:
            for line in stream:
                item = json.loads(line)
                base_ids.add((item["venue"], int(item["year"]), item["paper_id"]))
    matched = base_ids & index.keys()
    coverage = Counter(venue for venue, _, _ in matched)
    denominators = Counter(venue for venue, _, _ in base_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for key in sorted(matched):
            writer.writerow(index[key])
    result = {"baseline_records": len(base_ids), "author_rows": len(matched),
              "coverage_by_venue": {venue: {"with_authors": coverage[venue], "records": denominators[venue]}
                                    for venue in sorted(denominators)},
              "unmatched_baseline_records": len(base_ids - index.keys()),
              "raw_author_records_outside_scope": len(index.keys() - base_ids)}
    args.output.with_suffix(".coverage.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
