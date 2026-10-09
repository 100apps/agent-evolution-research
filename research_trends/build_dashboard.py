#!/usr/bin/env python3
"""Build a self-contained, source-separated local research dashboard."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path("research_trends")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value):
    if value in ("", None):
        return None
    return float(value) if "." in str(value) else int(value)


def run():
    o = read(ROOT / "data/processed/openalex_monthly_wide.csv")
    a = read(ROOT / "data/processed/arxiv_monthly_wide.csv")
    c = read(ROOT / "conferences/processed/shared_title_yearly.csv")
    openalex = [{key: (row[key] if key == "month" else number(row[key]))
                 for key in ("month", "ai_share_global_pct", "ai_share_cs_pct",
                             "ai_share_global_excl_first_day_pct", "first_day_share_global_pct",
                             "ai_primary_1702_works", "marketing_primary_1406_works",
                             "marketing_ai_vision_cotag_pct")} for row in o]
    arxiv = [{key: (row[key] if key == "month" else number(row[key]))
              for key in ("month", "all_arxiv_submissions", "core_ai_5_submissions",
                          "core_ai_5_share_all_pct", "core_ai_5_share_cs_plus_stat_ml_pct")}
             for row in a]
    conference = [{key: (number(row[key]) if key in ("year", "matching_titles",
                                                    "denominator_papers", "share_pct") else row[key])
                   for key in ("cohort", "year", "source_status", "axis", "tag", "matching_titles",
                               "denominator_papers", "share_pct")} for row in c]
    payload = json.dumps({"openalex": openalex, "arxiv": arxiv, "conference": conference},
                         ensure_ascii=False, separators=(",", ":"))
    output = ROOT / "reports/dashboard.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    print(json.dumps({"dashboard": str(output), "months": len(openalex),
                      "conference_rows": len(conference)}, ensure_ascii=False))


HTML = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>科研活动趋势｜来源分离数据面板</title>
<style>
body{margin:0;background:#f4f7fb;color:#13233d;font:15px/1.5 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:26px}h1{font-size:29px}h2{margin-top:0}
.lead,.note{color:#4b5d79}.box{background:white;border:1px solid #dae2eb;border-radius:12px;padding:22px;margin:20px 0}
select{padding:8px;font:inherit;border-radius:6px}svg{width:100%;height:auto;display:block}
table{border-collapse:collapse;width:100%}th,td{padding:5px 8px;border:1px solid #e0e6ee;text-align:center}
th:first-child{text-align:left}td small{display:block;color:#465978}
.scroll{overflow:auto}.bad{color:#8c3c26}
@media(max-width:600px){main{padding:14px}.box{padding:16px}h1{font-size:25px}
.scroll::before{content:'左右滑动查看其他年份 →';display:block;color:#4b5d79;font-size:13px;padding-bottom:8px}
table{font-size:12px}th:first-child{position:sticky;left:0;background:white;min-width:145px;z-index:1}}
</style>
<main><h1>AI 与相邻科研活动：可核验来源</h1>
<p class="lead">2020-01—2026-09 月度：OpenAlex 与 arXiv 分开展示；顶会按会场年份展示。数字为论文或作品，不是研究人员人数。2026 最近月可能回填；NeurIPS 2026 仅暂定 program，不进入完整三会合计。</p>
<section class="box"><h2>月度论文活动</h2><label>指标 <select id="metric">
<optgroup label="OpenAlex 当前主主题"><option value="oa:ai_share_global_pct">AI 1702 / 全球作品 (%)</option>
<option value="oa:ai_share_cs_pct">AI 1702 / 计算机作品 (%)</option>
<option value="oa:ai_share_global_excl_first_day_pct">剔除月首日：AI / 全球 (%)</option>
<option value="oa:first_day_share_global_pct">月首日作品占比 (%)</option>
<option value="oa:ai_primary_1702_works">AI 1702 作品数</option>
<option value="oa:marketing_primary_1406_works">营销 1406 作品数</option>
<option value="oa:marketing_ai_vision_cotag_pct">营销中 AI/视觉共标签 (%)</option></optgroup>
<optgroup label="arXiv 首次提交类别"><option value="ax:core_ai_5_share_all_pct">core5 / 全 arXiv (%)</option>
<option value="ax:core_ai_5_share_cs_plus_stat_ml_pct">core5 / CS+stat.ML (%)</option>
<option value="ax:core_ai_5_submissions">core5 提交数</option>
<option value="ax:all_arxiv_submissions">全 arXiv 提交数</option></optgroup></select></label>
<svg id="plot" viewBox="0 0 1000 370" role="img" aria-label="月度论文活动折线图"></svg>
<p id="point" class="note">悬停、聚焦或触摸数据点查看月值。</p>
<p class="note">OpenAlex 的 AI 1702 是当前分类器主子领域，抽样中出现量子与地质作品；arXiv core5 是类别并集。两个来源总体和时间字段不同，曲线不能相加。OpenAlex 月首日堆积尤其明显，剔除首日仅诊断。</p></section>
<section class="box"><h2>顶会标题词：一套规则跨五会场</h2>
<p class="note">下表每格为命中标题数及其占该会场该年主会题录的百分比。方法词与任务词允许重叠，标题不含某词不等于不用该方法。</p>
<label>会场 <select id="cohort"><option>ML_three</option><option>ICML</option><option>ICLR</option><option>NeurIPS</option><option>ACL</option><option>CVPR</option><option>ML_ICML_ICLR</option></select></label>
<div class="scroll"><table id="heat"></table></div>
<p class="note bad">NeurIPS 2026 是未完成的会场 program；ML_three 仅有 2020—2025 完整三会。其他会场是各自官方 proceedings 或 accepted-main-program 口径，不能推断全球人员转行。</p></section>
<section class="box"><h2>核查文件</h2><p>分析协议、查询 URL、UTC 时间、原始响应 SHA、失败/缺失、共享标题规则与逐论文标签见本目录的 README 和 data/conferences 文件夹。年/月不得混成同一频率。</p></section></main>
<script>
const D=__DATA__;
const metric=document.getElementById("metric"),plot=document.getElementById("plot"),point=document.getElementById("point");
function svgEl(name,attrs){let e=document.createElementNS("http://www.w3.org/2000/svg",name);for(let k in attrs)e.setAttribute(k,attrs[k]);plot.appendChild(e);return e}
function draw(){
let v=metric.value.split(":"),rows=v[0]==="oa"?D.openalex:D.arxiv,key=v[1],vals=rows.map(r=>r[key]),good=vals.filter(x=>x!==null);
let compact=window.innerWidth<600,w=compact?420:1000,h=compact?225:370,left=compact?42:65,right=compact?405:945,top=compact?20:35,bottom=compact?180:325;
plot.setAttribute("viewBox","0 0 "+w+" "+h);
let max=Math.max(...good)*1.08,n=rows.length,x=i=>left+i*(right-left)/(n-1),y=a=>bottom-a*(bottom-top)/max;
plot.innerHTML="";svgEl("rect",{x:x(n-12),y:top,width:right-x(n-12),height:bottom-top,fill:"#fff3e5"});
for(let j=0;j<=4;j++){let q=j*max/4;svgEl("line",{x1:left,y1:y(q),x2:right,y2:y(q),stroke:"#d7e0eb"});let t=svgEl("text",{x:left-7,y:y(q)+4,"text-anchor":"end","font-size":compact?10:12,fill:"#4b5d79"});t.textContent=q.toFixed(key.includes("submissions")||key.includes("works")?0:1)}
let pts=vals.map((a,i)=>a===null?null:x(i)+","+y(a)).filter(Boolean);
svgEl("polyline",{points:pts.join(" "),fill:"none",stroke:v[0]==="oa"?"#145ea8":"#a34535","stroke-width":2.5});
vals.forEach((a,i)=>{if(a===null)return;let p=svgEl("circle",{cx:x(i),cy:y(a),r:3.2,fill:v[0]==="oa"?"#145ea8":"#a34535",tabindex:0});p.onmouseenter=p.onfocus=p.onpointerdown=()=>point.textContent=rows[i].month+"："+a.toLocaleString("zh-CN")+(key.endsWith("_pct")?"%":" 篇")});
for(let i=0;i<n;i+=compact?24:12){let t=svgEl("text",{x:x(i),y:h-8,"text-anchor":"middle","font-size":compact?10:12,fill:"#4b5d79"});t.textContent=rows[i].month}
}
const cohort=document.getElementById("cohort"),heat=document.getElementById("heat");
let labels=["explicit_language_foundation","historical_pretrained_cues","pretraining_selfsupervision","posttraining_adaptation","agents_tools_broad","explicit_lm_agent_title_candidate","inference_systems_compute","evaluation_safety","optimization_theory","classical_statistics","search_retrieval","recommendation","marketing_advertising","software_code","nlp_language_tasks","vision_perception","robotics_control"];
function table(){
let rows=D.conference.filter(r=>r.cohort===cohort.value),years=[...new Set(rows.map(r=>r.year))].sort(),map=new Map(rows.map(r=>[r.tag+"|"+r.year,r]));
heat.innerHTML="";let head=document.createElement("tr");head.innerHTML="<th>词条</th>"+years.map(y=>"<th>"+y+"</th>").join("");heat.appendChild(head);
labels.forEach(tag=>{let tr=document.createElement("tr"),rmax=Math.max(...years.map(y=>map.get(tag+"|"+y)?.share_pct??0));let th=document.createElement("th");th.textContent=tag;tr.appendChild(th);
years.forEach(y=>{let r=map.get(tag+"|"+y),td=document.createElement("td");if(r){let alpha=.06+.58*(rmax?r.share_pct/rmax:0);td.style.background="rgba(20,94,168,"+alpha+")";td.title=r.matching_titles+" / "+r.denominator_papers+"；"+r.source_status;td.innerHTML=r.share_pct.toFixed(2)+"%<small>"+r.matching_titles+" / "+r.denominator_papers+"</small>";if(r.source_status==="provisional_incomplete")td.style.outline="2px dashed #a34535"}tr.appendChild(td)});heat.appendChild(tr)});
}
metric.onchange=draw;cohort.onchange=table;window.addEventListener("resize",draw);draw();table();
</script></html>"""


if __name__ == "__main__":
    run()
