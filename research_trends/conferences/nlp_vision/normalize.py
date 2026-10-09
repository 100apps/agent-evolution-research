#!/usr/bin/env python3
"""Parse the cached official ACL/CVPR main-proceedings bibliography."""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).parent
RAW = ROOT / "raw"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def element_text(element):
    return clean("".join(element.itertext())) if element is not None else ""


def provenance(name):
    obj = json.loads((RAW / (name + ".manifest.json")).read_text(encoding="utf-8"))
    if not obj.get("sha256"):
        raise ValueError(f"missing raw source: {name}")
    return obj


class CVFParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.in_link = False
        self.link = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "dt":
            self.in_title = "ptitle" in attrs.get("class", "").split()
        if tag == "a" and self.in_title:
            self.in_link = True
            self.link = {"href": attrs.get("href"), "parts": []}

    def handle_data(self, data):
        if self.in_link and self.link is not None:
            self.link["parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.in_link:
            self.rows.append({"href": self.link["href"], "title": clean("".join(self.link["parts"]))})
            self.link = None
            self.in_link = False
        if tag == "dt":
            self.in_title = False


def save_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def save_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader()
        writer.writerows(rows)


def main():
    main_rows, excluded, coverage, tracks = [], [], [], []
    for year in range(2020, 2027):
        name = f"acl_{year}.xml"
        source = provenance(name)
        root = ET.parse(RAW / name).getroot()
        acl_rows, per_track = [], {}
        for volume in root.findall("volume"):
            track = volume.attrib["id"]
            papers = volume.findall("paper")
            included = track in ("main", "long", "short")
            tracks.append({"venue": "ACL", "year": year, "track": track,
                           "volume_title": element_text(volume.find("meta/booktitle")),
                           "records": len(papers), "included_main": included})
            if included:
                per_track[track] = len(papers)
            for paper in papers:
                paper_id = f"{root.attrib['id']}-{track}.{paper.attrib['id']}"
                retract = paper.find("retracted")
                row = {"paper_id": paper_id, "venue": "ACL", "year": year,
                       "track": track, "title": element_text(paper.find("title")),
                       "abstract": element_text(paper.find("abstract")),
                       "official_url": f"https://aclanthology.org/{paper_id}/",
                       "publication_status": "retracted" if retract is not None else "no_retraction_flag_in_xml",
                       "retraction_date": retract.get("date", "") if retract is not None else "",
                       "source_type": "published_main_proceedings" if included else "excluded_auxiliary_track",
                       "source_url": source["source_url"], "source_sha256": source["sha256"],
                       "source_fetched_at_utc": source["fetched_at_utc"]}
                (acl_rows if included else excluded).append(row)
        main_rows.extend(acl_rows)
        coverage.append({"venue": "ACL", "year": year, "records": len(acl_rows),
                         "abstracts_present": sum(bool(row["abstract"]) for row in acl_rows),
                         "retracted": sum(row["publication_status"] == "retracted" for row in acl_rows),
                         "tracks": per_track, "source_files": [name], "complete_for_source": True,
                         "scope": "official main/long/short XML volumes; excludes Findings/workshops/demos"})
        names = ([f"cvpr_2020_day{day}.html" for day in (16, 17, 18)] if year == 2020
                 else [f"cvpr_{year}.html"])
        cvpr_rows, seen, raw_entries = [], set(), 0
        for cvpr_name in names:
            cvpr_source = provenance(cvpr_name)
            parser = CVFParser()
            parser.feed((RAW / cvpr_name).read_text(encoding="utf-8"))
            raw_entries += len(parser.rows)
            for item in parser.rows:
                url = urljoin("https://openaccess.thecvf.com/", item["href"] or "")
                if url in seen:
                    continue
                if "CVPRW" in url or "workshop" in url.lower():
                    raise ValueError(f"workshop URL in main index: {url}")
                seen.add(url)
                cvpr_rows.append({"paper_id": "CVF:" + url.split(".com/", 1)[1],
                                  "venue": "CVPR", "year": year, "track": "main", "title": item["title"],
                                  "abstract": "", "official_url": url,
                                  "publication_status": "not_verified_from_index", "retraction_date": "",
                                  "source_type": "published_main_proceedings",
                                  "source_url": cvpr_source["source_url"], "source_sha256": cvpr_source["sha256"],
                                  "source_fetched_at_utc": cvpr_source["fetched_at_utc"]})
        main_rows.extend(cvpr_rows)
        coverage.append({"venue": "CVPR", "year": year, "records": len(cvpr_rows),
                         "raw_entries": raw_entries, "abstracts_present": 0,
                         "tracks": {"main": len(cvpr_rows)}, "source_files": names,
                         "complete_for_source": True,
                         "scope": "official CVF main index; 2020 union of three days; workshops excluded"})
    if any(not row["title"] or not row["paper_id"] for row in main_rows):
        raise ValueError("empty main paper title or ID")
    if len(main_rows) != len({(row["venue"], row["year"], row["paper_id"]) for row in main_rows}):
        raise ValueError("duplicate main paper IDs")
    main_rows.sort(key=lambda row: (row["venue"], row["year"], row["paper_id"]))
    save_jsonl(ROOT / "papers_main.jsonl", main_rows)
    save_csv(ROOT / "papers_main.csv", main_rows)
    save_jsonl(ROOT / "acl_auxiliary_excluded.jsonl", excluded)
    save_csv(ROOT / "track_inventory.csv", tracks)
    save_csv(ROOT / "coverage_summary.csv", [{"venue": row["venue"], "year": row["year"],
                                                "records": row["records"],
                                                "abstracts_present": row["abstracts_present"],
                                                "source_files": "|".join(row["source_files"])} for row in coverage])
    (ROOT / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(main_rows), "coverage": coverage}, ensure_ascii=False))


if __name__ == "__main__":
    main()
