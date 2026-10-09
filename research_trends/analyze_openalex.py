#!/usr/bin/env python3
"""Turn cached OpenAlex monthly query results into auditable tables and an offline chart."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from collect_openalex import FIRST_MONTH, LAST_MONTH, months, query


def write_csv(path: Path, rows: list[dict], columns: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def load_long(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = [(r["month"], r["metric"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate month/metric rows")
    return dict(zip(keys, rows))


def integer(row: dict | None, field: str) -> int | None:
    if not row or row.get("status") != "ok" or row.get(field, "") == "":
        return None
    return int(row[field])


def ratio(n: int | None, d: int | None) -> float | None:
    return round(100 * n / d, 6) if n is not None and d not in (None, 0) else None


def analyze(data_dir: Path, report_path: Path):
    source = load_long(data_dir / "openalex_monthly.csv")
    first_days = load_long(data_dir / "openalex_first_day.csv") if (data_dir / "openalex_first_day.csv").exists() else {}
    marketing = load_long(data_dir / "openalex_marketing.csv") if (data_dir / "openalex_marketing.csv").exists() else {}
    monthly = []
    fields = []
    for month in months(FIRST_MONTH, LAST_MONTH):
        global_row = source.get((month, "global_and_fields"))
        ai_row = source.get((month, "ai_primary_1702"))
        vision_row = source.get((month, "ai_vision_primary_1702_1707"))
        total = integer(global_row, "count")
        cs = integer(global_row, "cs_field_17_count")
        ai = integer(ai_row, "count")
        ai_vision = integer(vision_row, "count")
        unknown = integer(global_row, "unknown_field_count")
        first_global_row = first_days.get((month, "global_and_fields"))
        day1_total = integer(first_global_row, "count")
        day1_cs = integer(first_global_row, "cs_field_17_count")
        day1_ai = integer(first_days.get((month, "ai_primary_1702")), "count")
        day1_ai_vision = integer(first_days.get((month, "ai_vision_primary_1702_1707")), "count")
        marketing_total = integer(marketing.get((month, "marketing_primary_1406")), "count")
        marketing_cotag = integer(marketing.get((month, "marketing_with_ai_vision_cotag")), "count")
        if all(x is not None for x in (total, cs, ai, ai_vision)) and not (ai <= ai_vision <= cs <= total):
            raise ValueError(f"inconsistent nested proxy counts: {month}")
        if marketing_total is not None and marketing_cotag is not None and marketing_cotag > marketing_total:
            raise ValueError(f"marketing co-tag exceeds domain total: {month}")
        if all(x is not None for x in (day1_total, day1_cs, day1_ai, day1_ai_vision)) and not (
                day1_ai <= day1_ai_vision <= day1_cs <= day1_total):
            raise ValueError(f"inconsistent first-day proxy counts: {month}")
        rem_total = total - day1_total if total is not None and day1_total is not None else None
        rem_cs = cs - day1_cs if cs is not None and day1_cs is not None else None
        rem_ai = ai - day1_ai if ai is not None and day1_ai is not None else None
        rem_ai_vision = ai_vision - day1_ai_vision if ai_vision is not None and day1_ai_vision is not None else None
        monthly.append({
            "month": month, "global_eligible_works": total, "cs_primary_field_works": cs,
            "ai_primary_1702_works": ai, "ai_vision_primary_1702_1707_works": ai_vision,
            "unknown_primary_field_works": unknown, "ai_share_global_pct": ratio(ai, total),
            "ai_share_cs_pct": ratio(ai, cs), "ai_vision_share_global_pct": ratio(ai_vision, total),
            "ai_vision_share_cs_pct": ratio(ai_vision, cs),
            "first_day_global_works": day1_total, "first_day_cs_works": day1_cs,
            "first_day_ai_works": day1_ai, "first_day_ai_vision_works": day1_ai_vision,
            "first_day_share_global_pct": ratio(day1_total, total),
            "ai_share_global_excl_first_day_pct": ratio(rem_ai, rem_total),
            "ai_share_cs_excl_first_day_pct": ratio(rem_ai, rem_cs),
            "ai_vision_share_cs_excl_first_day_pct": ratio(rem_ai_vision, rem_cs),
            "marketing_primary_1406_works": marketing_total,
            "marketing_ai_vision_cotag_works": marketing_cotag,
            "marketing_share_global_pct": ratio(marketing_total, total),
            "marketing_ai_vision_cotag_pct": ratio(marketing_cotag, marketing_total),
            "recent_within_3m": month >= "2026-07", "recent_within_6m": month >= "2026-04",
            "recent_within_12m": month >= "2025-10",
            "status": "ok" if all(x is not None for x in (total, cs, ai, ai_vision, unknown)) else "missing",
            "source_vintage": "OpenAlex API; captured 2026-10-09 UTC",
        })
        url = query(month, "global_and_fields")
        raw_path = data_dir / "raw" / "openalex" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if not raw_path.exists():
            continue
        raw = raw_path.read_bytes()
        obj = json.loads(raw)
        for group in obj.get("group_by", []):
            fields.append({"month": month, "field_id": str(group["key"]).rstrip("/").split("/")[-1],
                           "field_name": group.get("key_display_name"), "works": group["count"],
                           "share_global_pct": ratio(group["count"], total),
                           "raw_sha256": hashlib.sha256(raw).hexdigest()})
    output = data_dir / "processed"
    write_csv(output / "openalex_monthly_wide.csv", monthly, list(monthly[0]))
    write_csv(output / "openalex_fields_monthly.csv", fields, list(fields[0]))
    annual = []
    for year in range(2020, 2027):
        members = [r for r in monthly if r["month"].startswith(str(year))]
        complete_calendar = len(members) == 12
        valid = complete_calendar and all(r["status"] == "ok" for r in members)
        row = {"year": year, "calendar_months_observed": len(members),
               "status": "ok" if valid else "partial_or_missing"}
        for key in ("global_eligible_works", "cs_primary_field_works", "ai_primary_1702_works",
                    "ai_vision_primary_1702_1707_works", "unknown_primary_field_works"):
            row[key] = sum(r[key] for r in members) if valid else None
        row["ai_share_global_pct"] = ratio(row["ai_primary_1702_works"], row["global_eligible_works"])
        row["ai_share_cs_pct"] = ratio(row["ai_primary_1702_works"], row["cs_primary_field_works"])
        row["ai_vision_share_cs_pct"] = ratio(row["ai_vision_primary_1702_1707_works"], row["cs_primary_field_works"])
        for key in ("first_day_global_works", "first_day_cs_works", "first_day_ai_works", "first_day_ai_vision_works",
                    "marketing_primary_1406_works", "marketing_ai_vision_cotag_works"):
            row[key] = sum(r[key] for r in members) if valid and all(r[key] is not None for r in members) else None
        row["first_day_share_global_pct"] = ratio(row["first_day_global_works"], row["global_eligible_works"])
        row["marketing_share_global_pct"] = ratio(row["marketing_primary_1406_works"], row["global_eligible_works"])
        row["marketing_ai_vision_cotag_pct"] = ratio(row["marketing_ai_vision_cotag_works"], row["marketing_primary_1406_works"])
        annual.append(row)
    write_csv(output / "openalex_annual.csv", annual, list(annual[0]))
    field_totals = {}
    field_names = {}
    for field in fields:
        key = (field["month"][:4], field["field_id"])
        field_totals[key] = field_totals.get(key, 0) + field["works"]
        field_names[field["field_id"]] = field["field_name"]
    field_annual = [{"year": year, "field_id": fid, "field_name": field_names[fid], "works": value}
                    for (year, fid), value in sorted(field_totals.items()) if year != "2026"]
    write_csv(output / "openalex_fields_annual.csv", field_annual, list(field_annual[0]))
    if not all(r["status"] == "ok" for r in monthly):
        status = "incomplete"
    else:
        status = "complete_queries_recent_months_provisional"
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "status": status,
               "months_expected": 81, "months_ok": sum(r["status"] == "ok" for r in monthly),
               "first_month": FIRST_MONTH, "last_calendar_month": LAST_MONTH,
               "annual": annual, "september_pilot": [r for r in monthly if r["month"] in ("2020-09", "2023-09", "2026-09")],
               "definitions": {"unit": "OpenAlex default-core work ID", "date": "primary-location publication_date",
                               "eligible_types": "article|preprint|conference-paper|review", "AI_narrow": "primary subfield 1702",
                               "AI_plus_vision": "primary subfield 1702 or 1707", "CS": "primary field 17",
                               "marketing": "primary subfield 1406; AI co-tag means one of top-three topics has subfield 1702 or 1707",
                               "exclude_first_day": "diagnostic sensitivity only; not a correction for date imputation"}}
    (output / "openalex_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    chart_data = json.dumps(monthly, ensure_ascii=False, separators=(",", ":"))
    report_path.write_text(HTML.replace("__DATA__", chart_data), encoding="utf-8")
    print(json.dumps({"months_ok": summary["months_ok"], "annual_ok": sum(r["status"] == "ok" for r in annual),
                      "fields_rows": len(fields), "report": str(report_path)}, ensure_ascii=False))


HTML = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>AI 科研活动趋势 · OpenAlex</title>
<style>body{font:16px/1.6 system-ui,sans-serif;color:#14213d;background:#f6f8fb;margin:0}main{max-width:1080px;margin:auto;padding:32px}h1{line-height:1.2}p{max-width:900px}.card{background:white;border:1px solid #dce3ed;border-radius:12px;padding:20px;margin:20px 0;box-shadow:0 2px 10px #1231}select{font:inherit;padding:8px}svg{width:100%;height:420px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #dce3ed;text-align:right;padding:5px}td:first-child,th:first-child{text-align:left}.note{color:#4d5f7b;font-size:14px}.legend{display:flex;gap:24px}.chip{width:14px;height:14px;display:inline-block;margin-right:6px}.bad{color:#8b3a23}</style>
<main><h1>科研论文活动中的 AI 主分类</h1><p>OpenAlex 当前 core 语料；2020-01—2026-09。每个值是被索引作品数，不是研究人员人数。2026 近月索引尚未证明成熟；图中浅色区为最近 12 个月。</p>
<div class="card"><label>查看指标 <select id="metric"><option value="ai_share_global_pct">AI / 全部研究作品 (%)</option><option value="ai_share_cs_pct">AI / 计算机科学作品 (%)</option><option value="ai_share_global_excl_first_day_pct">剔除每月首日：AI / 全部 (%)</option><option value="first_day_share_global_pct">每月首日占比 (%)</option><option value="ai_vision_share_global_pct">AI+视觉 / 全部 (%)</option><option value="ai_vision_share_cs_pct">AI+视觉 / 计算机科学 (%)</option><option value="ai_primary_1702_works">AI 主分类作品数</option><option value="marketing_primary_1406_works">营销主分类作品数</option><option value="marketing_ai_vision_cotag_pct">营销中 AI+视觉共标签 (%)</option><option value="global_eligible_works">全部合格作品数</option><option value="cs_primary_field_works">计算机科学作品数</option></select></label><svg id="chart" viewBox="0 0 1000 420" role="img" aria-label="月度趋势图"></svg><div id="hover" class="note">鼠标悬停在点上可查看月值。</div></div>
<div class="card"><h2>同月样本</h2><table><thead><tr><th>月份</th><th>全部作品</th><th>计算机</th><th>AI 1702</th><th>AI / 全部</th><th>AI / 计算机</th></tr></thead><tbody id="pilots"></tbody></table></div>
<p class="note">口径：article、preprint、conference-paper、review；排除已知撤稿；每项按主主题，1702 是 OpenAlex 人工智能子领域。1707 计算机视觉为敏感性扩展，仍非所有用 AI 的论文。营销为主子领域 1406；AI+视觉共标签只表示当前分类器前三主题中同时出现 1702/1707。OpenAlex 会回填出版日期和更改分类。2026-10 主题分类器更新后，本图统一采用本次回溯抓取版本。详细 URL、原始响应 SHA 和缺失见数据目录。</p>
<p class="note bad">禁止由这张图推断全球研究人员转行。论文发表滞后、数据库收录与一月首日日期堆积均可能改变月形状。</p></main>
<script>const data=__DATA__;const svg=document.getElementById('chart'),hover=document.getElementById('hover'),select=document.getElementById('metric');function draw(){const key=select.value, v=data.map(d=>d[key]), mx=Math.max(...v.filter(x=>x!==null))*1.08, n=v.length, x=i=>65+i*880/(n-1), y=a=>365-a*310/mx;svg.innerHTML='';function el(tag,attrs){const z=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,q] of Object.entries(attrs))z.setAttribute(k,q);svg.appendChild(z);return z}el('rect',{x:x(n-12),y:35,width:945-x(n-12),height:330,fill:'#fff4e8'});for(let i=0;i<=4;i++){let q=i*mx/4;el('line',{x1:65,y1:y(q),x2:945,y2:y(q),stroke:'#d8e1ea'});let t=el('text',{x:55,y:y(q)+4,'text-anchor':'end',fill:'#52647d','font-size':12});t.textContent=q.toFixed(key.endsWith('works')?0:1)}let points=v.map((a,i)=>a===null?null:[x(i),y(a)]).filter(Boolean);el('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#145ea8','stroke-width':2.5});v.forEach((a,i)=>{if(a===null)return;let c=el('circle',{cx:x(i),cy:y(a),r:3,fill:'#145ea8',tabindex:0});c.onmouseenter=c.onfocus=()=>hover.textContent=data[i].month+'：'+a.toLocaleString('zh-CN')+(key.endsWith('_pct')?'%':' 篇');});for(let i=0;i<n;i+=12){let t=el('text',{x:x(i),y:395,'text-anchor':'middle',fill:'#52647d','font-size':12});t.textContent=data[i].month}}select.onchange=draw;draw();document.getElementById('pilots').innerHTML=data.filter(d=>['2020-09','2023-09','2026-09'].includes(d.month)).map(d=>`<tr><td>${d.month}${d.month==='2026-09'?'（暂定）':''}</td><td>${d.global_eligible_works?.toLocaleString('zh-CN')??'缺失'}</td><td>${d.cs_primary_field_works?.toLocaleString('zh-CN')??'缺失'}</td><td>${d.ai_primary_1702_works?.toLocaleString('zh-CN')??'缺失'}</td><td>${d.ai_share_global_pct??'缺失'}%</td><td>${d.ai_share_cs_pct??'缺失'}%</td></tr>`).join('');</script></html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("research_trends/data"))
    parser.add_argument("--report", type=Path, default=Path("research_trends/reports/trends.html"))
    args = parser.parse_args()
    analyze(args.data_dir, args.report)
