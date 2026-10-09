#!/usr/bin/env python3
"""Build a public-safe, self-contained Pages copy of the offline research report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup


REPOSITORY_URL = "https://github.com/100apps/agent-evolution-research"
SITE_URL = "https://100apps.github.io/agent-evolution-research/"
TREND_URL = SITE_URL + "research-trends/"
EXPLORER_URL = TREND_URL + "explorer/"
PANORAMA_PATH = "assets/Agent_自进化论文全景图.png"
FORBIDDEN_PUBLIC_PATTERNS = {
    "Windows user path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.IGNORECASE),
    "WSL user path": re.compile(r"/mnt/[a-z]/Users/", re.IGNORECASE),
    "Unix home path": re.compile(r"/(?:home|Users)/[^/\s]+/", re.IGNORECASE),
    "file URL": re.compile(r"file://", re.IGNORECASE),
    "known local username": re.compile(r"guangfeng", re.IGNORECASE),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_blob_url(relative_path: str) -> str:
    encoded = quote(relative_path.replace("\\", "/"), safe="/")
    return f"{REPOSITORY_URL}/blob/main/{encoded}"


def canonical_paper_url(paper: dict[str, object]) -> str:
    """Return a stable public landing page from the registry's canonical identity."""
    paper_id = str(paper.get("paper_id", ""))
    namespace, separator, value = paper_id.partition(":")
    if not separator or not value:
        raise SystemExit(f"invalid paper identity: {paper_id!r}")
    if namespace == "arxiv":
        return f"https://arxiv.org/abs/{value}"
    if namespace == "pmlr":
        volume, dash, slug = value.partition("-")
        if not dash or not volume.startswith("v") or not slug:
            raise SystemExit(f"invalid PMLR identity: {paper_id}")
        return f"https://proceedings.mlr.press/{volume}/{slug}.html"
    if namespace == "acl":
        return f"https://aclanthology.org/{value}/"
    raise SystemExit(f"unsupported paper identity: {paper_id}")


def set_link_text(anchor, text: str) -> None:
    anchor.clear()
    anchor.append(text)


def build(repo: Path, staging: Path) -> dict[str, object]:
    source_html = repo / "reports" / "index.html"
    registry_path = repo / "metadata" / "paper_registry.json"
    if not source_html.is_file() or not registry_path.is_file():
        raise SystemExit("source report or paper registry is missing")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    papers = registry.get("papers", [])
    if len(papers) != 39:
        raise SystemExit(f"expected 39 registered papers, found {len(papers)}")

    paper_links: dict[str, str] = {}
    source_urls: list[str] = []
    for paper in papers:
        urls = paper.get("source_urls") or []
        if not urls:
            raise SystemExit(f"paper has no verified public source: {paper.get('paper_id')}")
        public_url = canonical_paper_url(paper)
        if urlparse(public_url).scheme not in {"http", "https"}:
            raise SystemExit(f"paper source is not HTTP(S): {public_url}")
        local_pdf = paper.get("local_pdf")
        if not local_pdf:
            raise SystemExit(f"paper has no local PDF identity: {paper.get('paper_id')}")
        paper_links["../" + local_pdf.replace("\\", "/")] = public_url
        source_urls.append(public_url)

    soup = BeautifulSoup(source_html.read_text(encoding="utf-8"), "html.parser")

    if soup.title:
        soup.title.string = "Agent 自动优化 / Agent 进化：39 篇论文在线报告"

    description = soup.new_tag("meta")
    description["name"] = "description"
    description["content"] = "Agent 自动优化与 Agent 进化的 39 篇论文地图、证据审计与可复现实验报告。"
    soup.head.append(description)

    extra_style = soup.new_tag("style")
    extra_style["id"] = "public-site-style"
    extra_style.string = """
.public-notice{margin:18px auto;padding:16px 18px;border:1px solid #b7d7c8;border-radius:14px;background:#eef9f3;color:#173c2d}
.public-notice strong{color:#0c6b45}.public-boundary{border-left:4px solid #0c6b45}
a[data-access=repository]{border-style:dashed!important}.publication-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
"""
    soup.head.append(extra_style)

    replacements = {
        "证据优先 · 可离线打开": "证据优先 · 公开在线版",
        "本地校验页数": "已核验页数",
        "3 项本地实跑": "3 项已实跑",
    }
    for text_node in list(soup.find_all(string=True)):
        value = str(text_node)
        updated = value
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != value:
            text_node.replace_with(updated)

    nav = soup.find("nav")
    if nav:
        for anchor in nav.find_all("a", href="#files"):
            set_link_text(anchor, "公开版边界")
        notice_fragment = BeautifulSoup(
            """
<div class="wrap public-notice public-boundary" role="note">
  <strong>公开在线版。</strong>
  论文入口指向作者、arXiv、OpenReview、PMLR、ACL 等公开原文；本站不托管论文 PDF、全文提取、原始数据或实验日志。
  研究代码和归档链接直接指向公开 GitHub 仓库。<a href="{TREND_URL}">查看 AI 科研活动趋势</a> · <a href="{EXPLORER_URL}">浏览十会议论文目录</a>。
</div>
""".replace("{TREND_URL}", TREND_URL).replace("{EXPLORER_URL}", EXPLORER_URL),
            "html.parser",
        )
        nav.insert_after(notice_fragment.div)

    for paragraph in list(soup.select("p.small")):
        if paragraph.get_text(" ", strip=True).startswith("本地原文："):
            paragraph.decompose()

    converted_papers = 0
    converted_repository = 0
    embedded_panorama_links = 0
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if href in paper_links:
            anchor["href"] = paper_links[href]
            anchor["data-public-source"] = "verified-paper-source"
            if "本地 PDF" in anchor.get_text(" ", strip=True):
                set_link_text(anchor, "公开原文")
            converted_papers += 1
        elif href.startswith("../"):
            relative = href[3:].replace("\\", "/")
            if relative == PANORAMA_PATH:
                anchor["href"] = "#panorama"
                set_link_text(anchor, "页面内嵌全景图")
                embedded_panorama_links += 1
            else:
                anchor["href"] = repository_blob_url(relative)
                label = anchor.get_text(" ", strip=True) or Path(relative).name
                if "研究仓库" not in label:
                    label += "（研究仓库）"
                set_link_text(anchor, label)
                anchor["data-access"] = "repository"
                converted_repository += 1

    if converted_papers != 39:
        raise SystemExit(f"expected to convert 39 local PDF links, converted {converted_papers}")

    for container in soup.select(".links"):
        seen: set[str] = set()
        for anchor in list(container.find_all("a", href=True, recursive=False)):
            href = anchor["href"]
            if href in seen and urlparse(href).scheme in {"http", "https"}:
                anchor.decompose()
            else:
                seen.add(href)

    for anchor in soup.find_all("a", href=True):
        if urlparse(anchor["href"]).scheme in {"http", "https"}:
            anchor["target"] = "_blank"
            anchor["rel"] = "noopener noreferrer"

    files_section = soup.find(id="files")
    if not files_section:
        raise SystemExit("report has no #files section")
    replacement = BeautifulSoup(
        f"""
<section id="files">
  <div class="wrap">
    <div class="section-title"><h2>公开版边界与验证</h2></div>
    <div class="publication-grid">
      <div class="panel"><h3>论文入口</h3><p>39 篇唯一论文均链接到已核验的作者、arXiv、OpenReview、PMLR、ACL 或出版方页面。本站不复制或托管论文 PDF。</p></div>
      <div class="panel"><h3>研究归档</h3><p>代码、结构化数据、全文提取与真实运行日志不复制进 Pages 产物；相关链接直接指向公开研究仓库。</p><div class="links"><a data-access="repository" target="_blank" rel="noopener noreferrer" href="{REPOSITORY_URL}">公开研究仓库</a></div></div>
      <div class="panel"><h3>证据等级</h3><p>完整论文结果复现 0；缩小规模方法复现 0；发布工件离线重放 1；合成机制示例 2。其余内容为论文作者报告、来源核验或待执行计划。</p></div>
    </div>
    <p class="small">公开构建只允许发布原报告首页、独立趋势面板与 Pages 标记文件；全景图以 data URI 内嵌。构建检查会拒绝 PDF、原始日志、研究笔记、元数据、绝对本地路径及凭据样式内容。</p>
  </div>
</section>
""",
        "html.parser",
    ).section
    files_section.replace_with(replacement)

    footer = soup.find("footer")
    if footer:
        footer.clear()
        wrap = soup.new_tag("div")
        wrap["class"] = "wrap"
        wrap.string = "Agent 自动优化 / Agent 进化研究 · 公开在线报告 · 不含论文 PDF、原始数据、日志或凭据。"
        footer.append(wrap)

    relative_links = sorted(
        {
            anchor["href"]
            for anchor in soup.find_all("a", href=True)
            if not anchor["href"].startswith("#") and not urlparse(anchor["href"]).scheme
        }
    )
    if relative_links:
        raise SystemExit(f"public report still has relative links: {relative_links}")

    panorama_images = [
        image
        for image in soup.find_all("img", src=True)
        if image["src"].startswith("data:image/png;base64,")
    ]
    if len(panorama_images) != 1:
        raise SystemExit(f"expected one embedded panorama, found {len(panorama_images)}")

    html = str(soup)
    repository_links = len(soup.select('a[data-access="repository"]'))
    privacy_hits = [name for name, pattern in FORBIDDEN_PUBLIC_PATTERNS.items() if pattern.search(html)]
    if privacy_hits:
        raise SystemExit(f"public report contains forbidden local data: {privacy_hits}")

    dist = staging / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    output_html = dist / "index.html"
    output_html.write_text(html, encoding="utf-8", newline="\n")
    (dist / ".nojekyll").write_text("", encoding="utf-8")

    trend_source = repo / "research_trends" / "reports" / "dashboard.html"
    if not trend_source.is_file():
        raise SystemExit("trend dashboard is missing")
    trend_html = trend_source.read_text(encoding="utf-8")
    if trend_html.count("<main><h1>") != 1 or "不是研究人员人数" not in trend_html:
        raise SystemExit("trend dashboard layout or evidence boundary changed")
    trend_links = (
        f'<nav aria-label="研究导航"><a href="{SITE_URL}">39 篇 Agent 进化论文报告</a>'
        f' · <a href="{EXPLORER_URL}">十会议论文 CSV Explorer</a>'
        f' · <a href="{REPOSITORY_URL}/tree/main/research_trends">复核数据与研究过程</a></nav>'
    )
    trend_html = trend_html.replace("<main><h1>", "<main>" + trend_links + "<h1>", 1)
    trend_privacy_hits = [name for name, pattern in FORBIDDEN_PUBLIC_PATTERNS.items()
                          if pattern.search(trend_html)]
    if trend_privacy_hits:
        raise SystemExit(f"trend dashboard contains forbidden local data: {trend_privacy_hits}")
    trend_output = dist / "research-trends" / "index.html"
    trend_output.parent.mkdir(parents=True, exist_ok=True)
    trend_output.write_text(trend_html, encoding="utf-8", newline="\n")

    catalog = repo / "research_trends" / "catalog"
    explorer = dist / "research-trends" / "explorer"
    explorer.mkdir(parents=True, exist_ok=True)
    explorer_sources = {
        "index.html": catalog / "explorer.html",
        "explorer_worker.js": catalog / "explorer_worker.js",
        "index_manifest.json": catalog / "index_manifest.json",
        "papers_index.jsonl.gz": catalog / "papers_index.jsonl.gz",
    }
    for name, source in explorer_sources.items():
        if not source.is_file():
            raise SystemExit(f"missing Explorer asset: {source}")
        target = explorer / name
        if name.endswith(".gz"):
            target.write_bytes(source.read_bytes())
        else:
            value = source.read_text(encoding="utf-8")
            hits = [label for label, pattern in FORBIDDEN_PUBLIC_PATTERNS.items() if pattern.search(value)]
            if hits:
                raise SystemExit(f"Explorer asset {name} contains forbidden local data: {hits}")
            target.write_text(value, encoding="utf-8", newline="\n")
    index_manifest = json.loads((explorer / "index_manifest.json").read_text(encoding="utf-8"))
    if index_manifest["row_count"] != 89530 or sha256(explorer / "papers_index.jsonl.gz") != index_manifest["data_sha256"]:
        raise SystemExit("Explorer index row count or SHA-256 mismatch")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": "reports/index.html",
        "paper_registry": "metadata/paper_registry.json",
        "registered_papers": len(papers),
        "converted_local_pdf_links": converted_papers,
        "repository_links_labeled": repository_links,
        "embedded_panorama_links": embedded_panorama_links,
        "embedded_panorama_images": len(panorama_images),
        "unique_verified_paper_sources": len(set(source_urls)),
        "remaining_relative_links": relative_links,
        "privacy_hits": privacy_hits,
        "dist_files": ["dist/.nojekyll", "dist/index.html", "dist/research-trends/index.html"] +
        ["dist/research-trends/explorer/" + name for name in explorer_sources],
        "index_bytes": output_html.stat().st_size,
        "index_sha256": sha256(output_html),
        "trend_index_bytes": trend_output.stat().st_size,
        "trend_index_sha256": sha256(trend_output),
        "trend_privacy_hits": trend_privacy_hits,
    }
    (staging / "build_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (staging / "paper_source_urls.txt").write_text(
        "\n".join(sorted(set(source_urls))) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.repo.resolve(), args.staging.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


