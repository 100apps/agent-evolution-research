#!/usr/bin/env python3
"""Build the stable paper registry from repository-local verified metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "metadata" / "paper_registry.json"
NOTE_BY_INDEX = {
    **{i: "research_notes/harness.md" for i in [1, 8, 9, 14, 15, 32, 34, 35, 37, 39]},
    **{i: "research_notes/skills.md" for i in [2, 3, 4, 5, 6, 7, 10]},
    **{i: "research_notes/skillforge_muse.md" for i in [12, 13, 36, 41]},
    **{i: "research_notes/prompts.md" for i in [16, 17, 18, 19, 21, 38]},
    **{i: "research_notes/training_routing.md" for i in [11, 22, 23, 24, 25, 26, 27, 28]},
    33: "research_notes/jitrl.md",
    **{i: "research_notes/systems_gui.md" for i in [29, 30, 40]},
    31: "research_notes/skvm_supplemental.md",
}


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def paper_id(filename: str) -> str:
    match = re.search(r"arxiv-(\d{4}\.\d{5})v\d+", filename)
    if match:
        return f"arxiv:{match.group(1)}"
    match = re.search(r"pmlr-(v\d+-[^.]+)\.pdf$", filename)
    if match:
        return f"pmlr:{match.group(1)}"
    match = re.search(r"acl-(.+)\.pdf$", filename)
    if match:
        return f"acl:{match.group(1)}"
    raise ValueError(f"cannot derive stable paper_id from {filename}")


def source_version(filename: str, url: str) -> str:
    match = re.search(r"(\d{4}\.\d{5})v(\d+)", filename + " " + url)
    if match:
        return f"arXiv {match.group(1)}v{match.group(2)}"
    if "pmlr-" in filename:
        return filename.removesuffix(".pdf").split("pmlr-", 1)[1]
    if "acl-" in filename:
        return filename.removesuffix(".pdf").split("acl-", 1)[1]
    return "source version encoded in filename"


def video_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"(BV[0-9A-Za-z]+)", url)
    return match.group(1) if match else None


def main() -> None:
    inventory = load("metadata/inventory.json")
    sources = load("metadata/download_sources.json")
    manifest = load("metadata/pdf_manifest.json")
    topic_map = load("metadata/agent_evolution_map.json")
    analysis = load("metadata/paper_analysis.json")

    inventory_by_index = {int(item["index"]): item for item in inventory["entries"]}
    manifest_by_filename = {item["filename"]: item for item in manifest["records"]}
    map_by_key: dict[str, tuple[dict, dict]] = {}
    for group in topic_map["groups"]:
        for paper in group["papers"]:
            key = str(paper["inventory_index"])
            if key in map_by_key:
                raise SystemExit(f"duplicate map key: {key}")
            map_by_key[key] = (group, paper)

    records = []
    for source in sources["core"]:
        index = int(source["index"])
        entry = inventory_by_index[index]
        group, map_paper = map_by_key[str(index)]
        pdf = manifest_by_filename[source["filename"]]
        records.append(
            {
                "paper_id": paper_id(source["filename"]),
                "collection_index": index,
                "supplemental_id": None,
                "video_id": video_id(entry["video_url"]),
                "video_url": entry["video_url"],
                "video_relation": "primary_collection_item",
                "primary_title": map_paper["primary_title"],
                "map_name": map_paper["name"],
                "theme_group_id": group["id"],
                "theme_group_title": group["title"],
                "source_urls": map_paper["source_urls"],
                "download_source_url": source["url"],
                "source_version": source_version(source["filename"], source["url"]),
                "local_pdf": pdf["path"].replace("\\", "/"),
                "local_text": pdf["text_path"].replace("\\", "/"),
                "pdf_sha256": pdf["sha256"],
                "pdf_bytes": pdf["bytes"],
                "pdf_pages": pdf["pages"],
                "analysis_file": NOTE_BY_INDEX[index],
                "analysis_section": f"合集条目 #{index}",
                "paper_analysis_key": str(index),
                "analysis_summary": analysis[str(index)],
                "evidence_levels": ["来源核验", "论文作者报告"],
            }
        )

    supplemental = sources["supplemental"][0]
    related_index = int(supplemental["related_to_index"])
    entry = inventory_by_index[related_index]
    group, map_paper = map_by_key["S01"]
    pdf = manifest_by_filename[supplemental["filename"]]
    records.append(
        {
            "paper_id": paper_id(supplemental["filename"]),
            "collection_index": None,
            "supplemental_id": "S01",
            "related_collection_index": related_index,
            "video_id": video_id(entry["video_url"]),
            "video_url": entry["video_url"],
            "video_relation": "referenced_by_commentary_video",
            "primary_title": map_paper["primary_title"],
            "map_name": map_paper["name"],
            "theme_group_id": group["id"],
            "theme_group_title": group["title"],
            "source_urls": map_paper["source_urls"],
            "download_source_url": supplemental["url"],
            "source_version": source_version(supplemental["filename"], supplemental["url"]),
            "local_pdf": pdf["path"].replace("\\", "/"),
            "local_text": pdf["text_path"].replace("\\", "/"),
            "pdf_sha256": pdf["sha256"],
            "pdf_bytes": pdf["bytes"],
            "pdf_pages": pdf["pages"],
            "analysis_file": NOTE_BY_INDEX[related_index],
            "analysis_section": "SkVM 补充论文（合集评论视频 #31 引用）",
            "paper_analysis_key": "31",
            "analysis_summary": analysis["31"],
            "evidence_levels": ["来源核验", "论文作者报告"],
        }
    )

    records.sort(key=lambda item: (item["collection_index"] is None, item["collection_index"] or 999))
    ids = [item["paper_id"] for item in records]
    if len(records) != 39 or len(ids) != len(set(ids)):
        raise SystemExit("registry must contain 39 unique paper_id values")
    map_keys = {str(item["collection_index"]) if item["collection_index"] is not None else item["supplemental_id"] for item in records}
    if map_keys != set(map_by_key):
        raise SystemExit("registry and topic map coverage differ")

    payload = {
        "schema_version": 1,
        "generated_from": [
            "metadata/inventory.json",
            "metadata/download_sources.json",
            "metadata/pdf_manifest.json",
            "metadata/paper_analysis.json",
            "metadata/agent_evolution_map.json",
        ],
        "count": len(records),
        "identity_rules": {
            "arxiv": "arxiv:<base-id>，版本单独保存在 source_version",
            "pmlr": "pmlr:<volume-paper-id>",
            "acl": "acl:<anthology-id>",
            "supplement": "SkVM 使用自身 arXiv ID；S01 只表示其地图/合集关系",
        },
        "papers": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "papers": len(records), "unique_ids": len(set(ids))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
