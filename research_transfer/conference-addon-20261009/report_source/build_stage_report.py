from pathlib import Path
import csv,json,html,base64,hashlib,math,shutil,zipfile,datetime
ROOT=Path('/workspace/shared/research_shift'); BASE=ROOT/'conferences'; OUT=ROOT/'conference_stage_report.html'; EVID=ROOT/'conference_stage_evidence'; EVID.mkdir(exist_ok=True)

def rows(p):
 with (BASE/p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def obj(p):return json.loads((BASE/p).read_text())
def esc(s):return html.escape(str(s),quote=True)
F=rows('comparison/fixed_basket_2020_2025.csv'); C=rows('comparison/venue_year_topic_counts.csv'); D=rows('comparison/fixed_basket_headline_deltas.csv'); V=rows('comparison/coverage_common.csv'); P=rows('comparison/paired_2025_2026.csv'); S=rows('nlp_vision/derived/title_tag_counts_shares.csv'); A=rows('audit/agent_abstract_audit.csv'); AS=obj('audit/audit_summary.json'); RULES=obj('comparison/common_topic_rules.json')
fi={(int(r['year']),r['topic']):r for r in F}; ci={(r['venue'],int(r['year']),r['topic']):r for r in C}; si={(r['venue'],int(r['year']),r['tag']):r for r in S}; di={r['topic']:r for r in D}
colors=['#067a78','#d47432','#495caa','#93609a','#566574']; chart_checks=[]
files=['comparison/fixed_basket_2020_2025.csv','comparison/fixed_basket_headline_deltas.csv','comparison/venue_year_topic_counts.csv','comparison/venue_2020_2025_deltas.csv','comparison/paired_2025_2026.csv','comparison/coverage_common.csv','comparison/common_topic_rules.json','comparison/validation.json','comparison/source_urls_by_venue_year.csv','comparison/change_decomposition.csv','comparison/osdi_2026_scopebreak_separate.csv','comparison/key_definition_sensitivities.csv','comparison/compare_titles.py','comparison/README_zh.md','comparison/source_corpus_manifest.json','ml/README_sources_coverage.md','ml/title_topic_rules.json','ml/annual_topic_counts.csv','nlp_vision/README.md','nlp_vision/derived/lexical_tag_rules.json','nlp_vision/derived/title_tag_counts_shares.csv','nlp_vision/derived/historical_pretrained_cue_sensitivity.csv','nlp_vision/coverage_summary.csv','nlp_vision/acceptance_count_checks.json','systems_ir/SOURCE_MEMO.md','systems_ir/title_lexicon.json','systems_ir/title_topic_counts.csv','systems_ir/systems/README.md','audit/agent_abstract_audit.csv','audit/audit_stratum_summary.csv','audit/sampling_manifest.json','audit/audit_summary.json','audit/validation.json','audit/README_方法与发现.md','audit/sample_agent_abstracts.py','audit/label_agent_abstracts.py']
for p in files:
 src=BASE/p
 if src.exists():
  dst=EVID/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def dl(p,label='下载图表数据 CSV'):
 content=(BASE/p).read_bytes();mime='text/csv' if p.endswith('.csv') else 'application/json';u=base64.b64encode(content).decode();return f'<a class="download" href="data:{mime};base64,{u}" download="{esc(Path(p).name)}">{label} ↗</a>'
def cite(url,label):return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'
def table(head,rs,cls=''):
 return '<div class="table-scroll"><table class="'+cls+'"><thead><tr>'+''.join('<th scope="col">'+esc(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in r)+'</tr>' for r in rs)+'</tbody></table></div>'
def detail_table(head,rs,title='查看完整图表数值'):
 return f'<details><summary>{title}</summary>'+table(head,rs)+'</details>'
def legend(labels):return '<div class="legend">'+''.join(f'<span><i style="background:{colors[i%len(colors)]}"></i>{esc(t)}</span>' for i,t in enumerate(labels))+'</div>'
def linechart(years,series,title,max_y=None,width=800,height=310):
 # Each series is label, list of (count, denominator); keep exact numbers for QA and accessible tables.
 ymax=max_y or max(1,math.ceil(max(n/d*100 if d else 0 for _,vals in series for n,d in vals)/5)*5)
 left,right,top,bottom=55,24,25,45;pw=width-left-right;ph=height-top-bottom
 svg=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>']
 for i in range(5):
  val=ymax*i/4;y=height-bottom-ph*i/4;svg +=[f'<line x1="{left}" x2="{width-right}" y1="{y}" y2="{y}" stroke="#dde4e4"/>',f'<text x="{left-10}" y="{y+4}" text-anchor="end">{val:g}%</text>']
 for i,year in enumerate(years):
  x=left+pw*i/(len(years)-1);svg.append(f'<text x="{x}" y="{height-14}" text-anchor="middle">{year}</text>')
 for j,(label,vals) in enumerate(series):
  pts=[]
  for i,(n,d) in enumerate(vals):
   value=n/d*100 if d else 0;x=left+pw*i/(len(years)-1);y=height-bottom-ph*value/ymax;pts.append((x,y,n,d,value));chart_checks.append({'figure':title,'series':label,'year':years[i],'count':n,'denominator':d,'share_pct':value})
  svg.append(f'<polyline points="'+ ' '.join(f'{x:.2f},{y:.2f}' for x,y,_,_,_ in pts)+f'" fill="none" stroke="{colors[j]}" stroke-width="3"/>')
  for x,y,n,d,val in pts:svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.6" fill="{colors[j]}"><title>{esc(label)} {n}/{d} = {val:.2f}%</title></circle>')
 svg.append('</svg>')
 data=[[year]+[f'{vals[i][0]:,}/{vals[i][1]:,} · {vals[i][0]/vals[i][1]*100:.2f}%' for _,vals in series] for i,year in enumerate(years)]
 return legend([s[0] for s in series])+'<div class="chart-scroll">'+''.join(svg)+'</div>'+detail_table(['年份']+[x[0] for x in series],data)
def common_series(topic,years=range(2020,2026),venue=None):
 out=[]
 for y in years:
  r=ci[(venue,y,topic)] if venue else fi[(y,topic)];out.append((int(r['count']),int(r['denominator'])))
 return out
def specialty_series(venue,tag):return [(int(si[(venue,y,tag)]['matching_titles']),int(si[(venue,y,tag)]['total_papers'])) for y in range(2020,2027)]
def fig(num,title,subtitle,body,source,note=''):
 return f'<figure id="figure{num}"><figcaption><span class="fig-no">图 {num:02}</span><h3>{title}</h3><p>{subtitle}</p></figcaption>{body}<div class="figure-foot"><span>{note}</span>{dl(source)}</div></figure>'
def kv(venue,y,topic):
 r=ci[(venue,y,topic)];return f"{int(r['count']):,}/{int(r['denominator']):,} · {float(r['share_pct']):.2f}%"

# Figure 1: stable panel, all annual points.
f1=fig(1,'研究标题的重心明显变化，但几条线同时增长','固定 9 会 · 2020–2025 · 同一套标题规则 · 各年论文数加权占比',linechart(list(range(2020,2026)),[(label,common_series(t)) for t,label in [('modern_or_historical','现代大模型或历史预训练词汇'),('generative','生成模型词汇'),('efficiency','效率／压缩／加速词汇'),('theory_optimization','理论／优化词汇')]],'固定九会标题主题占比',20),'comparison/fixed_basket_2020_2025.csv','多标签可重叠；不是相加等于 100% 的研究领域分区。')

# Figure 2: per-venue endpoints and exact count table.
venues=['ACL','CVPR','ICLR','ICML','NeurIPS','ICSE','KDD','SIGIR','OSDI']; width=820;left=112;right=160;top=40;rh=41;h=top+rh*9+35;xmax=45;plot=width-left-right
sg=[f'<svg viewBox="0 0 {width} {h}" role="img" aria-label="九个会议模型相关标题词汇占比的2020和2025对照"><title>同一规则下九个会议的模型词汇占比</title>']
for v in range(0,46,15):
 x=left+plot*v/xmax;sg.append(f'<line x1="{x}" x2="{x}" y1="25" y2="{h-25}" stroke="#dce5e4"/><text x="{x}" y="18" text-anchor="middle">{v}%</text>')
endrows=[]
for i,v in enumerate(venues):
 a=ci[(v,2020,'modern_or_historical')];b=ci[(v,2025,'modern_or_historical')];pa=float(a['share_pct']);pb=float(b['share_pct']);y=top+i*rh+10;xa=left+plot*pa/xmax;xb=left+plot*pb/xmax
 sg.extend([f'<text x="{left-15}" y="{y+5}" text-anchor="end" class="strong">{v}</text>',f'<line x1="{xa}" x2="{xb}" y1="{y}" y2="{y}" stroke="#a9cfc9" stroke-width="5"/>',f'<circle cx="{xa}" cy="{y}" r="5" fill="#fff" stroke="#667981" stroke-width="2"/>',f'<circle cx="{xb}" cy="{y}" r="5" fill="{colors[0]}"/>',f'<text x="{width-right+15}" y="{y+5}">{pa:.2f}% → {pb:.2f}%</text>'])
 endrows.append([v,kv(v,2020,'modern_or_historical'),kv(v,2025,'modern_or_historical')])
sg.append('</svg>')
f2=fig(2,'模型相关词汇的上升出现在多个会议内部','空心点 2020 · 实心点 2025 · 分母始终为该会议当年的主研究记录','<div class="chart-scroll">'+''.join(sg)+'</div>'+detail_table(['会议','2020 篇数／分母 · 份额','2025 篇数／分母 · 份额'],endrows),'comparison/venue_year_topic_counts.csv','口径：modern_or_historical，并非全部 AI 或全部预训练研究。')

# Figure 3: compare named phases without falsely assuming mutually exclusive stages.
f3=fig(3,'后训练、适配与推理成为更常见的显式研究问题','固定 9 会 · 同一规则 · 四类可以同时出现在一篇论文中',linechart(list(range(2020,2026)),[(label,common_series(t)) for t,label in [('reasoning_testtime','推理／测试时计算'),('finetuning_adaptation','微调／指令调优／适配'),('posttraining_named_broad','后训练／偏好方法（宽）'),('pretraining_explicit','显式预训练过程')]],'模型生命周期词汇年度份额',5),'comparison/fixed_basket_2020_2025.csv','“后训练宽口径”可能包含其他模型的偏好方法；加模型上下文门槛的结果另列。')

# Figure 4,5: local specialty lexicons, clearly isolated.
f4=fig(4,'ACL 的传统任务名降温，推理和检索更常见','ACL 主会长短文 · 2020–2026 · NLP 专用原始规则，不能与图 1–3 同名标签直接拼接',linechart(list(range(2020,2027)),[(label,specialty_series('ACL',t)) for t,label in [('translation','翻译'),('parsing_syntax','句法／解析'),('reasoning_planning','推理／规划'),('retrieval','检索')]],'ACL专用标题词汇趋势'),'nlp_vision/derived/title_tag_counts_shares.csv','份额下降是否伴随篇数下降，要同时查看数值表；标题命名变化也会影响结果。')
f5=fig(5,'CVPR 的变化是多模态与生成融入视觉，几何仍占重要位置','CVPR 主会索引 · 2020–2026 · CVPR 专用原始规则',linechart(list(range(2020,2027)),[(label,specialty_series('CVPR',t)) for t,label in [('3d_geometry','三维／几何'),('multimodal','多模态'),('diffusion','扩散'),('detection','检测')]],'CVPR专用标题词汇趋势',30),'nlp_vision/derived/title_tag_counts_shares.csv','2026 收集 4,042 条，官方录用公告为 4,089；差额原因未核实。')

# Figure 6: per-venue field continuity.
sm=[]
for v,t,label in [('ICSE','software_testing_analysis','测试／分析／修复'),('KDD','mining_temporal_anomaly','挖掘／时序／异常'),('SIGIR','retrieval_recommendation','检索／推荐')]:
 sm.append(f'<div class="small-chart"><h4>{v}</h4>'+linechart(list(range(2020,2027)),[('模型相关词汇',common_series('modern_or_historical',range(2020,2027),v)),(label,common_series(t,range(2020,2027),v))],v+'传统任务与模型词汇趋势',width=540,height=265)+'</div>')
f6=fig(6,'软件、挖掘和检索仍在做各自的问题','各会议内部年度占比 · 统一词典 · 三张图纵轴独立，避免把它们当作绝对大小排名','<div class="small-multiples">'+''.join(sm)+'</div>','comparison/venue_year_topic_counts.csv','主题可以交叉：一篇论文可以同时是软件测试研究和 LLM 研究。')

# Figure 7: 2026 paired panel with numbers, no fabricated common total.
pmap={(r['venue'],r['topic']):r for r in P}; topics=[('modern_or_historical','模型词汇'),('reasoning_testtime','推理／测试时'),('agents_broad','广义 agent'),('agents_language_action_strict','语言＋行动交集')]
heat=['<div class="table-scroll"><table class="heatmap"><thead><tr><th>会议</th>'+''.join('<th>'+label+'<small>2025 → 2026</small></th>' for _,label in topics)+'</tr></thead><tbody>']
for v in ['ACL','CVPR','ICLR','ICML','ICSE','KDD','SIGIR','SOSP']:
 heat.append('<tr><th scope="row">'+v+'</th>')
 for t,label in topics:
  r=pmap[(v,t)];pp=float(r['change_pp']);alpha=min(.22,abs(pp)/10*.22);color=f'rgba(6,122,120,{alpha:.3f})' if pp>=0 else f'rgba(212,116,50,{alpha:.3f})'
  heat.append(f'<td style="background:{color}"><b>{float(r["share_from_pct"]):.2f}% → {float(r["share_to_pct"]):.2f}%</b><small>{int(r["count_from"]):,}/{int(r["n_from"]):,} → {int(r["count_to"]):,}/{int(r["n_to"]):,}</small><em>{pp:+.2f} 个百分点</em></td>')
 heat.append('</tr>')
heat.append('</tbody></table></div>')
f7=fig(7,'2026 的加速信号更集中在推理和 agent 标题，而非所有模型词汇','仅逐会配对 2025 与 2026 · 不把不同会议集拼成一个总趋势',''.join(heat),'comparison/paired_2025_2026.csv','排除不完整的 NeurIPS 2026；OSDI 2026 因办会制度变动另列。SIGIR 2026 是初步录用名单。')

# Figure 8: category counts in the AI-assisted audit.
cats=[('n_central_llm_agent_loop','核心 LLM 行动闭环'),('n_non_llm_rl_multiagent','非 LLM RL／多主体'),('n_incidental_tool_memory_other','其他工具／记忆／对话'),('n_unclear_from_abstract','摘要不足以确认')];slabels={'ML_2020_2022':'ML 2020–2022','ML_2024_2026':'ML 2024–2026','ACL_2020_2022':'ACL 2020–2022','ACL_2024_2026':'ACL 2024–2026'}
auditbars=[];arows=[]
for r in AS['strata']:
 n=r['sample_n'];auditbars.append(f'<div class="audit-row"><div><b>{slabels[r["stratum"]]}</b><small>抽取 {n} / 可抽样 {r["eligible_abstract_papers"]:,}</small></div><div class="stack" role="img" aria-label="'+esc(', '.join(f'{label}{r[k]}篇' for k,label in cats))+'">'+''.join(f'<span style="width:{r[k]/n*100}%;background:{colors[i]}" title="{label}：{r[k]} 篇">{r[k] if r[k] else ""}</span>' for i,(k,label) in enumerate(cats))+'</div></div>')
 arows.append([slabels[r['stratum']],n]+[r[k] for k,_ in cats]+[f'{r["n_central_llm_agent_loop"]}/{n} = {r["n_central_llm_agent_loop"]/n*100:.1f}%'])
f8=fig(8,'同一个 agent 关键词，早期与近年的含义并不相同','60 篇标题阳性且有摘要的分层样本 · 单一 AI 辅助阅读者 · 非人工金标准',legend([label for _,label in cats])+''.join(auditbars)+detail_table(['分层','样本 n']+[l for _,l in cats]+['核心闭环比例'],arows),'audit/agent_abstract_audit.csv','图中的数是样本篇数；不是全会占比，不能估计标题漏检率。早期 0 不代表早期不存在。')

# Data tables and values.
coverage_rows=[]
for v in ['ICLR','ICML','NeurIPS','ACL','CVPR','ICSE','KDD','SIGIR','OSDI','SOSP']:
 r=[]
 for y in range(2020,2027):
  z=next(x for x in V if x['venue']==v and int(x['year'])==y);n=int(z['n_records'] or 0);txt=f'{n:,}' if n else '未举办';
  if v=='NeurIPS' and y==2026:txt+=' †'
  if v=='OSDI' and y==2026:txt+=' ‡'
  r.append(txt)
 coverage_rows.append([v]+r)
summary_topics=[('modern_or_historical','模型相关词汇（现代＋历史）'),('reasoning_testtime','推理／测试时计算'),('agents_broad','广义 agent／工具行动'),('agents_language_action_strict','语言上下文＋行动词交集'),('efficiency','效率／压缩／加速'),('theory_optimization','理论／优化'),('traditional_statistics','统计／概率传统方法'),('rl_control','强化学习／控制')]
summary_rows=[]
for t,label in summary_topics:
 r=di[t];summary_rows.append([label,f'{int(r["count_2020"]):,} · {float(r["pooled_2020_pct"]):.2f}%',f'{int(r["count_2025"]):,} · {float(r["pooled_2025_pct"]):.2f}%',f'{float(r["pooled_delta_pp"]):+.2f}',f'{float(r["equal_venue_delta_pp"]):+.2f}'])
methodrows=[]
for t,label in [('pretraining_explicit','显式预训练'),('pretrained_usage_cue','使用已预训练模型措辞'),('self_supervision','自监督／对比学习'),('posttraining_named_broad','后训练／偏好方法，宽口径'),('posttraining_model_context','后训练方法＋模型上下文'),('finetuning_adaptation','微调／适配'),('testtime_compute','仅测试时计算／搜索')]:
 r=di[t];methodrows.append([label,f'{int(r["count_2020"]):,} · {float(r["pooled_2020_pct"]):.2f}%',f'{int(r["count_2025"]):,} · {float(r["pooled_2025_pct"]):.2f}%'])
examples=[]
for aid in ['A24','A18','A52','A30']:
 r=next(a for a in A if a['audit_id']==aid);examples.append(f'<article class="paper"><div class="eyebrow">{r["venue"]} {r["year"]} · 抽样编号 {aid}</div><h4>{cite(r["paper_url"],r["title"])}</h4><p>{esc(r["rationale_zh"])}</p><p class="quote">摘要证据：“{esc(r["evidence_quote"])}”</p></article>')
boundaries=[]
for aid in ['A01','A09','A15']:
 r=next(a for a in A if a['audit_id']==aid);boundaries.append('<li>'+cite(r['paper_url'],r['title'])+'（'+r['venue']+' '+r['year']+'）：'+esc(r['rationale_zh'])+'</li>')

css='''
:root{--ink:#162e36;--muted:#5b7078;--teal:#067a78;--orange:#d47432;--paper:#fafbf8;--line:#dce5e4;--panel:#fff}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);font-family:Inter,"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif;font-size:16px;line-height:1.85}a{color:#086f75;text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#af5226}header{padding:64px 6vw 46px;border-bottom:1px solid var(--line);background:linear-gradient(140deg,#e6f1ec 0%,#fafbf8 70%)}.wrap{max-width:1130px;margin:auto}.eyebrow,.section-num{font-size:12px;text-transform:uppercase;letter-spacing:.15em;font-weight:750;color:var(--teal)}h1{font-size:clamp(32px,5vw,58px);line-height:1.2;margin:18px 0 20px;letter-spacing:-.04em;font-weight:780;max-width:880px}h2{font-size:clamp(25px,3vw,34px);line-height:1.35;margin:9px 0 20px;letter-spacing:-.025em}h3{font-size:23px;line-height:1.45;margin:8px 0}h4{font-size:17px;line-height:1.6;margin:6px 0}p{margin:12px 0}.lead{font-size:20px;max-width:925px;line-height:1.85}.muted{color:var(--muted)}.meta{font-size:13px;color:var(--muted);margin-top:26px}.status{display:inline-block;background:#fff7e8;color:#865721;padding:4px 10px;border:1px solid #e9d9b6;border-radius:4px;letter-spacing:.03em}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-top:36px}.metric{padding-top:18px;border-top:2px solid #b6cfc7}.metric b{display:block;font-size:34px;line-height:1.2;letter-spacing:-.025em}.metric span{display:block;font-size:13px;color:var(--muted);margin-top:8px}nav{border-bottom:1px solid var(--line);padding:14px 6vw;background:#fff;position:sticky;top:0;z-index:5;box-shadow:0 3px 10px #0b393d06}nav .wrap{display:flex;gap:26px;overflow:auto;white-space:nowrap}nav a{font-size:13px;text-decoration:none;font-weight:650}main{padding:15px 6vw 60px}section{padding-top:56px;scroll-margin-top:65px}section+section{margin-top:38px;border-top:1px solid var(--line)}.takeaways{display:grid;grid-template-columns:repeat(3,1fr);gap:30px}.takeaways article{border-top:3px solid var(--teal);padding-top:12px}.takeaways p{font-size:15px}.big{font-size:28px;font-weight:760;color:var(--teal)}.note{padding:18px 22px;background:#edf4f0;border-left:3px solid var(--teal);margin:25px 0}.warning{background:#fff7e9;border-left-color:#ce943e}.question{font-size:18px;font-weight:650;margin-top:28px}.interpret{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin:20px 0 28px}.interpret>div{padding-top:12px;border-top:1px solid var(--line)}.interpret b{display:block;color:var(--teal);font-size:13px;letter-spacing:.06em}.interpret p{font-size:15px}.figure-foot{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:14px;display:flex;justify-content:space-between;gap:20px;margin-top:16px}.download{white-space:nowrap;font-size:12px}figure{margin:30px 0;padding:27px 30px;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}figcaption p{font-size:13px;color:var(--muted);margin-top:7px}.fig-no{font-size:12px;font-weight:750;color:var(--teal);letter-spacing:.1em}.legend{display:flex;flex-wrap:wrap;gap:8px 23px;margin:20px 0 12px;font-size:12px}.legend span{display:flex;align-items:center;gap:7px}.legend i{width:11px;height:11px;display:inline-block;border-radius:2px}.chart-scroll{overflow:auto}.chart-scroll>svg{display:block;width:100%;min-width:580px;height:auto}svg text{font-family:inherit;font-size:13px;fill:#536973}svg .strong{font-weight:700;fill:var(--ink)}details{font-size:13px;margin-top:12px;border-top:1px solid #e4eae7;padding-top:11px}summary{cursor:pointer;color:#32646b}.table-scroll{overflow-x:auto;margin:15px 0}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.7;white-space:nowrap}th{font-weight:680;background:#edf3f0;text-align:left}th,td{padding:12px 14px;border-bottom:1px solid var(--line)}tbody tr:hover{background:#fafcfb}td:first-child{font-weight:600}.small-multiples{display:grid;grid-template-columns:1fr 1fr;gap:18px}.small-chart{min-width:0;padding:10px 0}.small-chart:last-child{grid-column:1/-1;max-width:610px}.small-chart .chart-scroll>svg{min-width:440px}.small-chart .legend{min-height:30px}.heatmap th,.heatmap td{padding:12px 13px}.heatmap td b{font-size:13px;font-weight:650}.heatmap small,.heatmap em{display:block;font-size:10px;color:var(--muted);font-style:normal;line-height:1.8}.heatmap small{margin-top:3px}.heatmap th small{font-weight:400}.audit-row{display:grid;grid-template-columns:180px 1fr;gap:22px;align-items:center;margin:20px 0}.audit-row small{display:block;font-size:11px;color:var(--muted)}.audit-row b{font-size:13px}.stack{display:flex;height:39px;overflow:hidden;border-radius:3px}.stack span{display:flex;justify-content:center;align-items:center;color:white;font-size:13px;font-weight:700}.papers{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px}.paper{padding:22px;border:1px solid var(--line);border-radius:5px;background:#fff}.paper p{font-size:14px}.paper .eyebrow{font-size:10px}.paper h4 a{color:var(--ink)}.quote{color:var(--muted);font-style:italic;font-size:12px!important}.claims{display:grid;grid-template-columns:1fr 1fr;gap:26px}.claims h4{border-bottom:1px solid var(--line);padding-bottom:10px}.claims li{font-size:14px;margin:10px 0}.recommendations{counter-reset:r;list-style:none;padding:0}.recommendations li{counter-increment:r;padding:22px 0 22px 55px;border-bottom:1px solid var(--line);position:relative}.recommendations li:before{content:counter(r,decimal-leading-zero);position:absolute;left:0;top:25px;font-size:23px;color:var(--teal);font-weight:700}.recommendations p{font-size:15px;margin:8px 0}.empty{padding:30px;border:1px dashed #b6c8c5;background:#f2f6f2}.empty b{font-size:22px;display:block}.two{display:grid;grid-template-columns:1fr 1fr;gap:28px}.source-list li{font-size:13px;margin:10px 0;overflow-wrap:anywhere}.filelist a{display:inline-block;margin:4px 15px 4px 0}footer{font-size:12px;padding:30px 6vw;border-top:1px solid var(--line);color:var(--muted);background:#eef4ef}.tag{font-size:11px;border:1px solid #bacdc8;border-radius:4px;padding:3px 7px}.nowrap{white-space:nowrap}.skip{position:absolute;top:-60px;left:15px;background:#fff;padding:10px}.skip:focus{top:10px;z-index:100}@media(max-width:700px){body{font-size:15px;line-height:1.85}header{padding:35px 6vw}.lead{font-size:17px}.metrics{grid-template-columns:1fr 1fr;gap:18px}.metric b{font-size:28px}nav{position:static}.takeaways,.interpret,.claims,.two,.papers,.small-multiples{grid-template-columns:1fr;gap:16px}.small-chart:last-child{grid-column:auto}.takeaways article{padding-bottom:10px}section{padding-top:36px}section+section{margin-top:28px}figure{padding:20px 16px;margin:24px -4px}h3{font-size:20px}.figure-foot{display:block}.figure-foot .download{display:block;margin-top:8px}.audit-row{grid-template-columns:1fr;gap:7px}.audit-row>div:first-child{display:flex;justify-content:space-between;gap:10px}table{font-size:12px}.note{padding:15px 17px}.empty{padding:22px}.chart-scroll:after{content:'图表可左右滚动查看';display:block;font-size:10px;color:#7a8e90;margin-top:3px}.source-list{padding-left:20px}}@media print{nav,.download{display:none}body{background:white;font-size:10pt}header{padding:20px 0}.wrap{max-width:none}main{padding:0}section{padding-top:25px}figure{break-inside:avoid;padding:15px}details:not([open])>*:not(summary){display:none}.chart-scroll>svg{min-width:0}h1{font-size:30pt}.paper{break-inside:avoid}footer{padding:20px 0}.table-scroll{overflow:visible}}
'''
content=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="计算机研究主题变化的会议阶段报告：十个会议、统一标题规则、逐会趋势与60篇Agent摘要抽样。"><title>计算机研究议题向哪里移动 · 会议阶段报告</title><style>{css}</style></head><body>
<a class="skip" href="#main">跳到正文</a>
<header><div class="wrap"><div class="eyebrow">研究趋势证据报告 · Conference stage · 2026-10-09</div><h1>计算机研究议题<br>向哪里移动</h1><p class="lead">大模型、生成、多模态、推理和行动型系统已成为更常见的论文主题。证据支持 Agent 研究的相关性；要证明一个 Agent 演化项目的价值，还需要可复现、可比较的机制证据。</p><p class="meta"><span class="status">阶段交付：会议证据已整合</span>　官方主研究列表／论文集，2020–2026 年可用版本。arXiv 与 OpenAlex 月度宏观数据已完成采集，尚未纳入本文件；这里不绘制其趋势。</p><div class="metrics"><div class="metric"><b>84,008</b><span>非临时会议论文记录<br>按会议 × 年份计数，非全球去重论文数</span></div><div class="metric"><b>10 个</b><span>计算机领域代表会议<br>固定跨年比较使用其中 9 个</span></div><div class="metric"><b>60 篇</b><span>标题＋摘要分层内容审计<br>AI 辅助单一阅读者</span></div><div class="metric"><b>8 张图</b><span>附分子、分母、规则与来源<br>所有图表可离线阅读</span></div></div></div></header>
<nav aria-label="报告目录"><div class="wrap"><a href="#conclusion">结论</a><a href="#common">统一比较</a><a href="#lifecycle">训练与推理</a><a href="#fields">各领域</a><a href="#latest">2026</a><a href="#agents">Agent 审计</a><a href="#project">项目判断</a><a href="#method">方法与来源</a></div></nav>
<main id="main" class="wrap">
<section id="conclusion"><div class="section-num">01 · 先看结论</div><h2>变化确实存在，三种过度推论仍不成立</h2><div class="takeaways"><article><div class="big">0.74% → 15.73%</div><h4>模型相关标题词汇大幅增加</h4><p>固定九会中，现代大模型或历史预训练模型词汇由 48/6,476 增至 2,817/17,907。使用包含通用语言模型措辞的更宽口径，则为 1.37% → 19.61%。这说明结果依赖明示词典，不能称为“全部大模型研究占比”。</p></article><article><div class="big">1.10% → 3.33%</div><h4>Agent 相关词增长，尚非多数</h4><p>广义 agent／工具行动词由 71 篇增至 597 篇。要求标题同时出现语言模型上下文与行动词后，2025 年为 194/17,907 = 1.08%。两种口径都不是经过语义验证的 LLM agent 总量。</p></article><article><div class="big">667 → 1,735 篇</div><h4>传统主题并未普遍缩小</h4><p>理论／优化词汇的论文数增加；论文加权份额为 10.30% → 9.69%，而会议等权份额为 7.15% → 7.49%。仅凭某个总占比，不能说理论研究衰退，更不能推断研究者迁移。</p></article></div>
<div class="note"><b>这份报告回答什么？</b> 所选顶级会议的主研究论文“标题中更常出现哪些问题”，以及抽取的 Agent 相关论文在摘要中“具体做什么”。它不测量全世界研究投入、人才流动、论文质量、产业采用率或项目新颖性。</div>
<p class="question">最稳妥的判断</p><p>研究议题正更多围绕模型能力、生成、推理、交互和效率展开；与此同时，软件测试、检索、三维几何、统计和系统仍保有大量工作。许多变化是<strong>原有问题与新模型结合</strong>，不同标签并不是互相替代的领域。</p></section>

<section id="common"><div class="section-num">02 · 同一把尺子</div><h2>固定会议和统一规则之后，变化仍然明显</h2><p>跨会议图采用一套新冻结的共同词典 common-title-v1.0，仅匹配标题。固定九会为 ACL、CVPR、ICLR、ICML、NeurIPS、ICSE、KDD、OSDI、SIGIR，覆盖 2020–2025 每一年。SOSP 在 2020、2022 未举办，不塞入固定年度分母；2026 的不完整和办会口径变化单独处理。</p>{f1}
<div class="interpret"><div><b>证据</b><p>生成模型词汇由 4.71% 增至 11.33%，多模态由 1.37% 增至 7.27%，效率／压缩／加速由 6.92% 增至 10.82%。模型词汇增长也出现在多个会议内部，并非只因为大会议扩容。</p></div><div><b>边界</b><p>固定会议名单仍会随每会规模变化而改变权重。因此同时报告论文加权和会议等权。共同词典中 diffusion 也可能命中图扩散等旧含义；理论词典也会命中应用论文的 optimization。</p></div></div>
{f2}
<h3>篇数与份额必须一起看</h3>{table(['统一标题标签','2020 篇数 · 份额','2025 篇数 · 份额','论文加权变化 pp','会议等权变化 pp'],summary_rows)}
<p class="muted">两列变化回答不同问题：论文加权是所收集论文的比例；会议等权是九个会议各占同样权重后的平均比例。它们都不是全球 CS 估计量。共同规则的数据分解显示，模型词汇 +14.99 个百分点中约 +14.98 来自会内份额变化，会议规模权重变化约 +0.01；这只是算术分解，不是因果识别。</p>
<p class="question">对阅读路线的含义</p><p>继续跟踪大模型相关能力与系统问题是有证据的；把所有传统领域都归入“过时”会遗漏大量新增工作。对技术负责人，更有用的是追踪“某类任务用什么方法、以什么成本得到什么结果”，而不是只追逐一个宽标签。</p></section>

<section id="lifecycle"><div class="section-num">03 · 模型生命周期</div><h2>“都转去做后训练与推理”需要拆成具体口径</h2><p>预训练、微调、偏好学习、推理时搜索和 Agent 控制是不同问题，同一篇论文可能同时涉及多项。把它们分开，可以避免把所有强化学习都算成 LLM 后训练，或把统计推断都算成推理时计算。</p>{f3}
{table(['具体标题信号','2020 篇数 · 份额','2025 篇数 · 份额'],methodrows)}
<div class="interpret"><div><b>能支持的观察</b><p>在标题层面，微调／适配、命名的后训练／偏好方法和推理相关问题都增长。预训练过程的显式标题占比也从 0.49% 升至 1.12%，并没有在这一口径下消失。</p></div><div><b>不能支持的观察</b><p>后训练宽口径为 277 篇，但要求模型上下文后仅 89 篇。区别既反映上下文歧义，也反映标题漏检，不能把任一数字当成真实总量。训练算力、项目预算和研究人员工时都没有被测量。</p></div></div>
<p class="muted">“推理／测试时计算”合并标签包含通用 reasoning；仅测试时计算／搜索的窄标签在 2025 年为 65 篇、0.36%。二者不能互换。</p></section>

<section id="fields"><div class="section-num">04 · 领域内部发生了什么</div><h2>从任务名转向模型能力，并不等于任务本身消失</h2><p>以下 ACL 与 CVPR 两图保留各领域原始专用规则，以展示翻译、解析、几何、检测等更细的主题。<strong>这两图不使用共同词典，不能把同名标签的数值与前后图直接拼接。</strong>完整规则和原始年度表已附在证据包中。</p>
{f4}<p>ACL 的翻译标题从 69/778（8.87%）变为 41/2,296（1.79%）；句法／解析从 57（7.33%）变为 24（1.05%）。这两项的篇数与份额都下降。对照而言，标题中的推理、检索和 agent 词更常见。传统语言任务也可能被写进大模型评测或能力分析中，标题计数无法追踪所有隐含任务。</p>
{f5}<p>CVPR 多模态由 38 篇增至 825 篇（2.59% → 20.41%）；三维／几何由 281 篇增至 825 篇（19.17% → 20.41%）。检测份额从 9.35% 降到 6.09%，但篇数从 137 增到 246。扩散在 2025 年达到 343/2,871（11.95%），2026 年为 338/4,042（8.36%）。因此“所有主题都单调转向扩散”的说法与数据不符。</p>
<p class="muted">专用词典与共同词典的一个可见差异：CVPR 2025 扩散专用口径 11.95%，共同口径 11.91%。这里保留不同规则的真实结果，不强行把它们改成一致。</p>
<h3>新模型进入老问题，领域身份仍然保留</h3>{f6}
<div class="interpret"><div><b>软件与信息领域</b><p>ICSE 测试／分析／修复词汇 2020 年为 35/129（27.13%），2025 年为 73/245（29.80%）。SIGIR 检索／推荐为 78/147（53.06%）→ 146/239（61.09%）。模型词汇同时增长，说明这些标签可以并存。</p></div><div><b>系统领域</b><p>OSDI 的模型词汇从 2020 年 0/70 到 2025 年 4/53；推理服务／GPU 基础设施从 3/70 到 5/53。SOSP 相应基础设施词汇 2025 年 9/66、2026 年 14/62。标题不能区分“用 AI 做系统”和“为 AI 工作负载做系统”，二者都值得读具体论文。</p></div></div>
<div class="note warning"><b>OSDI 2026 单列。</b> 研究论文 117 篇，另有 19 篇 Operational Systems；模型词汇 13/117（11.11%），推理服务／GPU 19/117（16.24%）。首次多轨、接收政策和审稿流程变化构成结构性断点，不能把从 53 到 117 篇的扩张全部归因于 AI。参见 {cite('https://www.usenix.org/sites/default/files/osdi26-message.pdf','官方主席说明')} 和 {cite('https://www.usenix.org/conference/osdi26/call-for-papers','官方征稿说明')}。</div></section>

<section id="latest"><div class="section-num">05 · 最新可用年份</div><h2>2026 要逐会看，不能用一个不完整的总盘子</h2><p>下面只配对同一会议的 2025 与 2026。ACL 模型相关词汇份额从 38.73% 降至 36.11%，但对应篇数从 658 增至 829；推理／测试时词汇和广义 agent 则明显增加。SIGIR 模型词汇也没有继续提高。真实变化比“一切向上”的故事更细。</p>{f7}
<p class="muted">所有 2026 数字都是截至本次采集、按会议年份记录的现有官方列表／论文集口径。不能把它们理解为未来不再变化的最终年度接受数量。NeurIPS 2026 的 5,522 条临时节目记录完整保留在源数据中，但不进入这里的可比结论。</p></section>

<section id="agents"><div class="section-num">06 · Agent 究竟在研究什么</div><h2>宽关键词会混入传统多主体、普通 RAG 和记忆模块</h2><p>本报告区分三个层次：① 标题出现广义 agent／工具行动词；② 标题同时出现语言模型上下文与行动词；③ 阅读摘要后，能确认语言模型作为决策／控制器，并以行动、观测或工具结果形成反馈闭环。第③层还包括直接训练、评测或验证这类流程。它是一个工作定义，不是学界统一标准。</p>
<p>为检查词义混杂，另用较宽的 agent／tool／memory 原始词典固定四个分层，从标题命中且有已收集摘要的 2,543 篇中抽取 60 篇，比较 2020–2022 与 2024–2026。排除 NeurIPS 2026、2023 年、CVPR、缺摘要及标题未命中的论文。抽样种子为 20261009；早期 ACL 的 11 篇全部读取。</p>{f8}
<div class="interpret"><div><b>审计读到了什么</b><p>60 篇中：15 篇可确认核心 LLM 行动闭环，23 篇为非 LLM RL／多主体，15 篇属于其他工具、记忆或对话用法，7 篇仅靠摘要无法确认。近期 ML 样本为 7/17，近期 ACL 为 8/16；这些是各自标题阳性样本内比例。</p></div><div><b>不能把 15/60 当成什么</b><p>各层抽样比例不同，直接合并并非总体估计；加权后的 39.5% 也只指所限定的标题阳性、有摘要总体。样本小且没有人工金标准、标题阴性抽样或全文审核，因此既不是全会 Agent 份额，也不提供召回率。</p></div></div>
<h3>四个摘要中明确可见的行动闭环</h3><p class="muted">这些论文均来自预先冻结的 60 篇样本，作为研究问题的例子，不是影响力排名。短证据已与本地官方来源摘要逐条核对；本阶段没有重新验证论文全文或实验结果。</p><div class="papers">{''.join(examples)}</div>
<h3>为什么早期的零不能解释成不存在</h3><ul class="source-list">{''.join(boundaries)}</ul>
<p>严格摘要证据门槛会保留这些边界项。若把所有“不确定”都改算为核心，近期 ML 的样本内比例为 52.9%，近期 ACL 为 62.5%。这是分类敏感性，不是置信区间，也不能排除其他标签仍有判断错误。</p>
<div class="note"><b>对 Agent 演化的直接提示：</b> 需要进一步分清研究对象是控制器、工具接口、记忆、环境、策略训练，还是仅把“agent”用于命名。即使确认行动闭环，也不自动说明系统发生了可迁移的演化。</div></section>

<section id="project"><div class="section-num">07 · 对 Agent 演化项目的判断</div><h2>趋势证明问题值得关注，复现与机制证明项目值得做</h2><p>项目背景是 {cite('https://github.com/100apps/agent-evolution-research','agent-evolution-research 仓库')} 及其 {cite('https://100apps.github.io/agent-evolution-research/','研究页面')}。根据本次项目盘点，当前整理 39 篇相关论文，涉及 harness、skills、prompts、topology、memory、post-training 和 JitRL 等路线；现有实验为 1 项 artifact replay、2 项合成实验，尚无完整复现。这里的 39 篇是项目文献集，不是全球随机样本，也不作为本报告的趋势分母。</p>
<div class="claims"><div><h4>这份会议证据可以支持</h4><ul><li>继续研究 LLM 交互系统与 Agent 演化有明确的议题相关性。</li><li>需要把传统多主体学习与现代语言行动闭环分开。</li><li>效率、推理、评测和软件任务可以构成有价值的相邻问题。</li></ul></div><div><h4>仍需项目实验自己证明</h4><ul><li>“演化”是否优于更简单的静态或搜索基线。</li><li>收益来自哪一层改变，能否跨任务、跨种子复现。</li><li>成本、数据泄漏、选择偏差和失败率是否可控。</li><li>相对于既有 39 篇及后续文献，新增贡献究竟是什么。</li></ul></div></div>
<ol class="recommendations"><li><h4>先完成一项真实任务上的完整复现</h4><p>选择代码、任务定义、评测和成本都可获得的一篇作为起点。把环境、模型版本、轨迹、失败和随机种子全部留下。artifact replay 和合成实验有辅助价值，但不能替代真实任务复现。</p></li><li><h4>用同一预算比较演化机制与简单基线</h4><p>至少区分静态 harness、无反馈随机搜索、等预算 best-of-N、带反馈的更新方法；按 token、工具调用、耗时和费用分别披露。只有在预算相当、评测独立时，才能解释收益。</p></li><li><h4>明确改变了什么，以及什么时候能保留下来</h4><p>分别追踪 prompts、skills、memory、topology、模型参数等对象；记录更新触发条件、反馈来源、保留／回滚规则和跨任务迁移。对每个机制做消融，避免把总体收益都归于“自我演化”。</p></li><li><h4>把项目贡献落在尚未解决的复现或评测缺口</h4><p>将既有论文按可用代码、模型依赖、环境稳定性、真实任务结果和负结果整理成竞争与复现矩阵。只有确认缺口后，再选择方法、基准或工具链贡献。热点增长本身不构成新颖性。</p></li></ol>
<p class="muted">以上是依据本阶段证据提出的研究建议，不是会议数据测出的因果结论，也不是对项目实验已成功的声明。本报告没有修改仓库或发布站点。</p></section>

<section id="method"><div class="section-num">08 · 范围与可复核性</div><h2>先固定分母，再解释主题</h2>
<div class="empty"><div class="eyebrow">arXiv / OpenAlex · 集成状态</div><b>月度宏观采集完成，尚未纳入本文件</b><p>另一路采集已报告完成 2020 年 1 月至 2026 年 9 月的月度宏观数据。本阶段 HTML 未导入其原始月度表或完成跨来源整合，因此不提供 arXiv 曲线、主题占比或与会议数据的合并估计。主题关键词试采样仍有失败缺口，不能当作完整主题序列。</p><p class="muted">这里保留空白是证据边界，不以会议年份、两端年度数字或示意数据填补月度结果。该部分应在下一轮核验原始 CSV、日期口径和分类映射后补入。</p></div>
<h3>逐会逐年实际记录数</h3>{table(['会议','2020','2021','2022','2023','2024','2025','2026'],coverage_rows)}
<p class="muted">† NeurIPS 2026 为 5,522 条不完整会前节目记录，排除主要比较。‡ OSDI 2026 仅 117 篇 Research，另 19 篇 Operational Systems 不在该表。总源记录 89,530，减临时 NeurIPS 2026 后为 84,008。SOSP 的“未举办”不是零研究需求。</p>
<div class="two"><div><h3>收录规则</h3><ul class="source-list"><li>NeurIPS／ICML／ICLR：主研究轨，按稳定论文 ID 去重；排除 position、datasets／benchmarks、journal-to-conference 等辅助轨。</li><li>ACL：主会 long／short，排除 Findings、workshop 等。历史撤稿标记保留并另有敏感性数据。</li><li>CVPR：CVF 主会索引，排除 workshops；CVPR 2020 取官方三天索引并集。</li><li>ICSE：research／technical；KDD：research；SIGIR：full／long。排除短文、工业、资源及新增的其他轨。</li><li>OSDI／SOSP：研究论文，排除邀请报告、海报等。接受名单与最终出版社论文集可能有差异。</li></ul></div><div><h3>必须带着读的限制</h3><ul class="source-list"><li>单位是会议年份的一条论文记录。未做跨会议、跨年份、跨 arXiv 的论文级去重。</li><li>词典仅是显式标题信号，多标签有交叉；没命中不等于不研究该主题。</li><li>标题词汇会随命名习惯而变；现代词不能抹去早期预训练模型研究。</li><li>ICLR 2020 缺 687 篇已采集摘要；CVPR 未批量采摘要。共同曲线始终只用标题。</li><li>CVPR 2026 索引比公告少 47 条；SIGIR 2026 声称 234 篇 full，实际可见 233 条。未虚构缺失记录。</li><li>词典回归测试、分母和数值校验不等于语义精确率／召回率验证。60 篇审计也不构成人工金标准。</li></ul></div></div>
<h3>三套规则的分工</h3>{table(['规则','在哪些图使用','可以怎样解读'],[['共同标题规则 v1.0','图 1、2、3、6、7','同一套规则用于跨会议、跨年度比较'],['ACL／CVPR 专用原始规则','图 4、5','只在各自会议内部看细分主题，不能拼接同名数值'],['agent／tool／memory 抽样规则＋摘要判断','图 8','从限定阳性总体检视词义，不给全会 Agent 流行率']])}
<p class="muted">共同标题处理：Unicode NFKC、casefold，将非 ASCII 字母／数字转为空格并合并空白，然后运行披露的正则。每个匹配保留题名、稳定 ID、规则和命中位置。比例为命中论文数 ÷ 相应主研究记录数；pp 是百分点。</p>
<h3>直接官方来源</h3><ul class="source-list"><li>机器学习：{cite('https://proceedings.mlr.press/','PMLR 论文集')}、{cite('https://papers.nips.cc/','NeurIPS 论文集')}、{cite('https://iclr.cc/FAQ/Proceedings','ICLR 论文集说明')}。每年准确导出地址见来源清单。</li><li>自然语言：{cite('https://raw.githubusercontent.com/acl-org/acl-anthology/master/data/xml/2026.acl.xml','ACL 官方 Anthology 2026 XML')}；视觉：{cite('https://openaccess.thecvf.com/CVPR2026?day=all','CVF CVPR 2026 主会索引')}。</li><li>信息检索：{cite('https://sigir2026.org/en-AU/pages/program/accepted-papers','SIGIR 2026 官方录用列表')}；全部 ICSE、KDD、SIGIR 年份的原始 URL 已逐年写入下载清单。</li><li>系统：{cite('https://www.usenix.org/sites/default/files/osdi26-message.pdf','OSDI 2026 主席说明')}、{cite('https://www.usenix.org/conference/osdi26/call-for-papers','OSDI 2026 征稿与轨道说明')}。SOSP 逐年官方列表和论文链接保留在元数据中。</li></ul>
<p>统计值来自本次对上述来源的提取与派生计算，官方页面不直接发布本报告的词典主题占比。各页抓取日期、来源类型和哈希保留在附带材料中。</p>
<div class="filelist">{dl('comparison/source_urls_by_venue_year.csv','下载逐会逐年来源 URL')}{dl('comparison/common_topic_rules.json','下载共同规则 JSON')}{dl('comparison/fixed_basket_headline_deltas.csv','下载摘要比较 CSV')}{dl('comparison/coverage_common.csv','下载覆盖范围 CSV')}{dl('audit/agent_abstract_audit.csv','下载 60 篇审计 CSV')}</div>
<h3>离线使用与证据包</h3><p>本 HTML 不依赖外部字体、脚本、图片或网络请求。图表和展开的数据表均已内嵌；CSV 下载链接内嵌了真实派生文件内容。外部论文链接需要联网。配套 conference_stage_evidence.zip 包含这些同名 CSV、规则、来源说明和校验文件，没有塞入体积巨大的全文元数据。</p><p class="muted">证据包足够复核本报告的汇总数字与判定依据；完整重跑采集仍需要原始快照或重新下载公开来源。包中的分类脚本不是已训练语义模型；冻结的 AI 审计标签不会由脚本自动重新判读。</p>
</section></main><footer><div class="wrap">会议阶段报告 · 数据快照 2026-10-09 UTC · 图表统计截至对应官方源采集版本<br>阅读提示：先看分母，再看份额；先区分词汇信号，再判断论文研究机制。</div></footer></body></html>'''
# Add the newly completed arXiv macro data without reusing either conference lexicon.
import io
mx=ROOT/'monthly_library_extract'; arx=json.loads((mx/'arxiv_monthly_wide.csv.read.json').read_text());oax=json.loads((mx/'openalex_monthly_wide.csv.read.json').read_text());reportx=json.loads((mx/'report_zh.md.read.json').read_text())
assert arx['has_more'] is False and oax['has_more'] is False
monthly_csv=arx['content'][1]; mr=list(csv.DictReader(io.StringIO(monthly_csv)));assert len(mr)==81
expected=[f'{2020+i//12:04d}-{1+i%12:02d}' for i in range(81)];assert [r['month'] for r in mr]==expected;assert all(r['status']=='ok' for r in mr)
for r in mr:
 for col,num,den in [('core_ai_5_share_all_pct','core_ai_5_submissions','all_arxiv_submissions'),('core_ai_5_share_cs_plus_stat_ml_pct','core_ai_5_submissions','cs_plus_stat_ml_submissions')]:
  assert abs(float(r[col])-int(r[num])/int(r[den])*100)<1e-6
md=EVID/'monthly';md.mkdir(exist_ok=True);(md/'arxiv_monthly_library_extracted.csv').write_text(monthly_csv,encoding='utf-8');(md/'openalex_monthly_library_extracted.csv').write_text(oax['content'][1],encoding='utf-8')
prov={'format':'Complete Library table parsed-text extraction; not original uploaded CSV bytes','retrieved_files':[{'name':x['name'],'library_file_id':x['library_file_id'],'has_more':x['has_more'],'original_declared_size_bytes':x['size_bytes'],'table_text_sha256':hashlib.sha256(x['content'][1].encode()).hexdigest()} for x in [arx,oax]],'month_count':81,'date_range':['2020-01','2026-09'],'arxiv_definition':'submittedDate UTC; category union cs.AI OR cs.LG OR cs.CL OR cs.CV OR stat.ML','note':'Generated index column preserved. SHA values refer to parsed table text, not original CSV bytes. OpenAlex mapping 1702 is not semantically pure AI, and first-day date heaping affects monthly shapes.'}
(md/'extraction_provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2),encoding='utf-8')
annual=[]
for y in range(2020,2026):
 r=[x for x in mr if x['month'].startswith(str(y))];alln=sum(int(x['all_arxiv_submissions']) for x in r);csn=sum(int(x['cs_plus_stat_ml_submissions']) for x in r);core=sum(int(x['core_ai_5_submissions']) for x in r);annual.append([y,f'{alln:,}',f'{csn:,}',f'{core:,}',f'{core/alln*100:.3f}%',f'{core/csn*100:.3f}%'])
assert annual[0][1:4]==['178,273','66,418','43,699'];assert annual[5][1:4]==['284,159','144,659','106,859']
w,h,left,right,top,bot=870,330,55,22,25,48;pw=w-left-right;ph=h-top-bot;svg=[f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="2020年1月至2026年9月arXiv core5类别并集的81个月份额"><title>arXiv core5类别并集的81个月度份额</title>']
recent_i=69;rx=left+pw*recent_i/80;svg.append(f'<rect x="{rx}" y="{top}" width="{w-right-rx}" height="{ph}" fill="#fff3dd"/><text x="{rx+7}" y="{top+16}" font-size="10">近月需防回填</text>')
for val in [0,20,40,60,80]:
 yy=h-bot-ph*val/90;svg.append(f'<line x1="{left}" x2="{w-right}" y1="{yy}" y2="{yy}" stroke="#dce5e4"/><text x="{left-9}" y="{yy+4}" text-anchor="end">{val}%</text>')
for i,r in enumerate(mr):
 if i%12==0 or i==80:
  xx=left+pw*i/80;lab=r['month'] if i==80 else r['month'][:4];svg.append(f'<text x="{xx}" y="{h-16}" text-anchor="middle">{lab}</text>')
for j,(col,label,den) in enumerate([('core_ai_5_share_all_pct','core5 / 全部 arXiv','all_arxiv_submissions'),('core_ai_5_share_cs_plus_stat_ml_pct','core5 / CS＋stat.ML','cs_plus_stat_ml_submissions')]):
 pts=[]
 for i,r in enumerate(mr):
  val=int(r['core_ai_5_submissions'])/int(r[den])*100;xx=left+pw*i/80;yy=h-bot-ph*val/90;pts.append((xx,yy));chart_checks.append({'figure':'arXiv monthly macro','series':label,'year':r['month'],'count':int(r['core_ai_5_submissions']),'denominator':int(r[den]),'share_pct':val})
 svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)+f'" fill="none" stroke="{colors[j]}" stroke-width="2.7"/>')
 for i,(xx,yy) in enumerate(pts):svg.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="2.1" fill="{colors[j]}"><title>{mr[i]["month"]} {esc(label)} {float(mr[i][col]):.2f}%</title></circle>')
svg.append('</svg>')
mdl='<a class="download" href="data:text/csv;base64,'+base64.b64encode(monthly_csv.encode()).decode()+'" download="arxiv_monthly_library_extracted.csv">下载完整 81 个月表格 CSV ↗</a>'
macro=f'''<figure id="figure9"><figcaption><span class="fig-no">图 09 · 新增宏观对照</span><h3>arXiv 的固定 AI 类别并集占比也在上升</h3><p>2020-01 至 2026-09 · 全部 81 个实际月份 · 首次提交日期 UTC · 两个分母分别绘制</p></figcaption>{legend(['core5 / 全部 arXiv','core5 / CS＋stat.ML'])}<div class="chart-scroll">{''.join(svg)}</div>{detail_table(['月份','core5 篇数','全部 arXiv','CS＋stat.ML','core5／全部','core5／CS＋stat.ML'],[[r['month'],r['core_ai_5_submissions'],r['all_arxiv_submissions'],r['cs_plus_stat_ml_submissions'],f"{float(r['core_ai_5_share_all_pct']):.2f}%",f"{float(r['core_ai_5_share_cs_plus_stat_ml_pct']):.2f}%"] for r in mr],'查看全部 81 个月数值')}<div class="figure-foot"><span>类别并集不重复相加；曲线是类别分布，不是经过语义审核的全部 AI 研究。</span>{mdl}</div></figure>
<h3>完整年度按篇数加权，避免平均月比率的偏差</h3>{table(['年份','全部 arXiv','CS＋stat.ML','core5 并集','core5／全部','core5／CS＋stat.ML'],annual)}
<p>core5 定义为 cs.AI、cs.LG、cs.CL、cs.CV、stat.ML 的并集；第二个分母为 cs.* 或 stat.ML，比纯 CS 略宽。2020–2025，core5 从 43,699 增至 106,859，占全部提交从 24.512% 增至 37.605%。2026 只有九个月，不与完整年度直接比较。arXiv 自选提交和类别交叉限制了向全部科学研究的外推。见 {cite('https://info.arxiv.org/help/api/user-manual.html','arXiv 官方 API 手册')}。</p>
<div class="note warning"><b>OpenAlex 的分类和日期问题不能省略。</b> 已完成的另一套宏观数据使用当前主子领域 1702 作为 AI 代理；该类中包含量子计算、量子信息等主题，不能按字面解释为语义纯净的 AI。2020 年作品落在各月 1 日的比例为 37.61%，2025 年为 26.38%；2020 年 1 月更达 83.65%，显示日期精度会扭曲月形状。来源报告尚未证明具体填日机制。这里不把 OpenAlex 月线与 arXiv 叠加或相加，详见其 {cite('https://help.openalex.org/data/works/attributes/','作品属性定义')}。</div>
<p class="muted">新增表来自已交付月度 CSV 的完整 Library 表格读取结果，81 个月、has_more=false，已核对分子／分母和年度和。证据包保存该解析导出、生成的 index 列及溯源信息；它不是原上传文件的逐字节副本。没有将解析导出的哈希冒称为原始 CSV 哈希。</p>
<div class="empty"><div class="eyebrow">仍然未知的部分</div><b>可靠的月度 Agent／后训练细分仍未完成</b><p>六类关键词试采样 18 格中只有 10 格成功、8 格缺失，遇到 429 后停止。宽窄 Agent 词串并非经过语义验证的嵌套集合。缺失不补零，不从两点画连续增长曲线；会议年度标题结果也不冒充月度或半月结果。</p></div>'''
start=content.index('<div class="empty"><div class="eyebrow">arXiv / OpenAlex · 集成状态</div>');end=content.index('<h3>逐会逐年实际记录数</h3>',start);content=content[:start]+macro+content[end:]
content=content.replace('arXiv 与 OpenAlex 月度宏观数据已完成采集，尚未纳入本文件；这里不绘制其趋势。','附录已补入 arXiv 81 个月宏观曲线；Agent 月度细分仍有缺口，OpenAlex 分类与日期限制单独说明。').replace('<b>8 张图</b>','<b>9 张图</b>').replace('阶段交付：会议证据已整合','阶段交付：十会证据＋arXiv 宏观对照')
content=content.replace('图 1、2、3、6、7','图 1、2、3、6、7').replace('本 HTML 不依赖外部字体','图 9 使用独立 arXiv 类别口径，与会议标题规则不拼接。本 HTML 不依赖外部字体')

OUT.write_text(content,encoding='utf-8')
# Reproducibility subset and numeric validations.
assert sum(int(x['n_records'] or 0) for x in V)==89530
assert sum(int(x['n_records'] or 0) for x in V if not (x['venue']=='NeurIPS' and x['year']=='2026'))==84008
assert len(A)==60
assert sum(AS['unweighted_sample_counts'].values())==60
for r in C:
 assert int(r['count'])<=int(r['denominator'])
 assert abs(float(r['share_pct'])-int(r['count'])/int(r['denominator'])*100)<1e-8
for r in S:
 assert abs(float(r['share_pct'])-int(r['matching_titles'])/int(r['total_papers'])*100)<.0001
for r in chart_checks:
 assert abs(r['count']/r['denominator']*100-r['share_pct'])<1e-10
with (EVID/'report_chart_values.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(chart_checks[0]));w.writeheader();w.writerows(chart_checks)
# Source files may evolve during authoring; capture current copies again.
for p in files:
 src=BASE/p
 if src.exists():shutil.copy2(src,EVID/p)
readme='''# 会议阶段证据包\n\n包含主报告使用的派生表、共同及专用规则、来源覆盖说明、60篇AI辅助摘要审计、校验结果与脚本。\n\n主报告为 conference_stage_report.html（独立提供）；report_chart_values.csv 为报告折线图全部原始分子分母。CSV均为真实文件，未用示意数据。\n\n共同口径：comparison；ACL/CVPR专用口径：nlp_vision；摘要审计：audit。不要混用规则。\n\n完整元数据与原始HTML/JSON快照没有包含在此小型包内。compare_titles.py 重新运行需原始三个会议族JSONL输入，抽样脚本需原始ML/ACL元数据；仅此包不能重新采集全部数据。AI标签脚本应用已冻结判断，不自动重新做语义阅读。\n\n本包附月度CSV的Library解析导出与溯源文件，不是原上传CSV的逐字节副本。arXiv宏观月线已纳入图9；Agent等月度主题细分仍有缺口。\n'''
(EVID/'README_证据包.md').write_text(readme,encoding='utf-8')
shutil.copy2(Path(__file__),EVID/'build_stage_report.py')
manifest=[]
for p in sorted(EVID.rglob('*')):
 if p.is_file():manifest.append({'file':str(p.relative_to(EVID)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(EVID/'package_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
qa={'title':'Conference-stage report','html_bytes':OUT.stat().st_size,'figures':9,'nonprovisional_records':84008,'all_records':89530,'excluded_neurips_2026':5522,'audit_records':60,'chart_values':len(chart_checks),'numeric_checks':'passed','html_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'html_render_check':'pending'}
(ROOT/'conference_stage_report_validation.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
zip_path=ROOT/'conference_stage_evidence.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in EVID.rglob('*'):
  if p.is_file():z.write(p,str(p.relative_to(ROOT)))
print(json.dumps({'html':str(OUT),'html_bytes':OUT.stat().st_size,'zip':str(zip_path),'zip_bytes':zip_path.stat().st_size,'numeric_qa':qa},ensure_ascii=False,indent=2))
