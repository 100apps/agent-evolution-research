#!/usr/bin/env python3
"""Common title-only conference topic analysis. Python 3.9+, standard library only.
No network calls. Input is existing normalized JSONL from the three collectors.
Windows: py -3 -X utf8 compare_titles.py --root C:\\path\\to\\conferences
Custom input: --input FILE (repeatable); requires venue, year, title, stable_id/paper_id.
Rules intentionally measure lexical cues, not semantic labels or an exhaustive partition.
"""
import argparse, collections, csv, hashlib, json, re, sys, unicodedata
from pathlib import Path
from datetime import datetime, timezone

VERSION = 'common-title-v1.0'
VENUES = ['ACL','CVPR','ICLR','ICML','ICSE','KDD','NeurIPS','OSDI','SIGIR','SOSP']
BASKET = [v for v in VENUES if v != 'SOSP']
INPUTS = ['ml/metadata_main.jsonl','nlp_vision/papers_main.jsonl','systems_ir/combined_papers.jsonl']
EVIDENCE = ['ml/coverage.json','ml/README_sources_coverage.md','nlp_vision/coverage.json','nlp_vision/README.md','systems_ir/combined_coverage.json','systems_ir/SOURCE_MEMO.md','systems_ir/systems/README.md']
# Each pattern is matched against NFKC, case-folded, punctuation-to-space title text.
# Patterns are wrapped in word boundaries. Base tags are ORs; compositions explicitly AND/OR tags.
RULES = {
 'modern_foundation_llm': dict(label_zh='现代大模型/基础模型词汇', group='shared', patterns=[r'large (?:language|vision language|multimodal|vision|reasoning) models?',r'foundation models?',r'(?:m?llms?|vlms?|lvlms?|lmms?)',r'chat ?gpt',r'gpt ?[345](?:\b|\d)',r'llama(?: ?[234])?',r'qwen(?: ?[23])?',r'generative ai'], caveat='Explicit modern vocabulary; VLM/vision foundation terms included. Not all LMs, transformers or pretrained models. Named tokens may be ambiguous.'),
 'historical_pretrained': dict(label_zh='历史预训练模型词汇', group='shared', patterns=[r'bert',r'roberta',r'albert',r'electra',r'xlnet',r'elmo',r't5',r'bart',r'gpt ?2',r'pre ?trained language models?'], caveat='Historical model-name sensitivity, not an exhaustive census. Names such as BART/ALBERT can be ambiguous.'),
 'modern_or_historical': dict(label_zh='现代大模型或历史预训练词汇并集', group='sensitivity', any_of=['modern_foundation_llm','historical_pretrained']),
 'language_model_context': dict(label_zh='语言模型上下文词汇', group='context', patterns=[r'language models?',r'vision language models?',r'language vision models?'], any_of=['modern_foundation_llm','historical_pretrained'], caveat='Context gate only; it still depends on explicit wording.'),
 'reasoning': dict(label_zh='推理/思维链词汇', group='shared', patterns=[r'reasoning',r'chain of thoughts?',r'chains of thought',r'tree of thoughts?',r'step by step'], caveat='Includes symbolic/spatial/causal reasoning; not exclusively LLM reasoning.'),
 'testtime_compute': dict(label_zh='测试时计算/搜索词汇', group='shared', patterns=[r'test time (?:scal\w*|comput\w*|search|reason\w*|budget\w*)',r'inference time (?:scal\w*|comput\w*|search|reason\w*|budget\w*)',r'best of n',r'test time training'], caveat='Not plain inference or all test-time adaptation; test-time training explicitly included.'),
 'reasoning_testtime': dict(label_zh='推理或测试时计算词汇并集', group='shared', any_of=['reasoning','testtime_compute']),
 'agents_broad': dict(label_zh='广义智能体/工具行动词汇', group='shared', patterns=[r'agents?',r'agentic',r'multi ?agents?',r'tool (?:use|using|usage|calling|calls?|invocation|learning|augmented)',r'web navigation',r'computer use'], caveat='Includes traditional multi-agent RL and software agents; no autonomy/feedback-loop claim.'),
 'agents_language_action_strict': dict(label_zh='语言模型上下文且智能体/工具行动词汇', group='sensitivity', all_of=['language_model_context','agents_broad'], caveat='Strict lexical conjunction, NOT validated semantic evidence of an LLM observation-action feedback loop. Agent-memory alone is not counted.'),
 'pretraining_explicit': dict(label_zh='显式预训练过程词汇', group='shared', patterns=[r'pre ?training',r'pre ?train(?:s|ing)?'], caveat='Infinitive/process wording only; does not prove paper itself trains a base model.'),
 'pretrained_usage_cue': dict(label_zh='预训练模型/已预训练措辞', group='shared', patterns=[r'pre ?trained'], caveat='Adjectival wording; cannot establish whether paper trains, analyzes or merely uses an existing model.'),
 'self_supervision': dict(label_zh='自监督/对比学习词汇', group='shared', patterns=[r'self supervis\w*',r'contrastive learning']),
 'posttraining_named_broad': dict(label_zh='后训练/偏好学习方法词汇', group='shared', patterns=[r'post ?training',r'rlhf',r'rlaif',r'dpo',r'grpo',r'rlvr',r'direct preference optimi[sz]ation',r'group relative policy optimi[sz]ation',r'reinforcement learning (?:from|with) (?:human feedback|ai feedback|verifiable rewards?)',r'preference optimi[sz]ation',r'reward model(?:s|ing)?'], caveat='Method cues alone can be ambiguous, including reward-model papers outside language models.'),
 'posttraining_model_context': dict(label_zh='后训练方法且语言/生成模型上下文', group='sensitivity', all_of=['posttraining_named_broad','posttraining_context'], caveat='Requires title to name model context; excludes context-implicit DPO/RLHF titles. Not all fine-tuning, reinforcement learning or alignment.'),
 'posttraining_context': dict(label_zh='后训练模型上下文门槛', group='context', patterns=[r'diffusion models?',r'generative models?',r'text to (?:image|video)',r'image generation'], any_of=['language_model_context']),
 'finetuning_adaptation': dict(label_zh='微调/指令调优/适配词汇', group='shared', patterns=[r'fine ?tun\w*',r'instruction tun\w*',r'parameter efficient',r'lora',r'adapters?'], caveat='Broader adaptation signal; not equivalent to preference post-training.'),
 'retrieval': dict(label_zh='检索/排序词汇', group='shared', patterns=[r'retriev\w*',r'rerank\w*',r'ranking',r'rag',r'search engines?',r'web search'], caveat='Includes conventional IR and RAG; not all search algorithms.'),
 'recommendation': dict(label_zh='推荐词汇', group='shared', patterns=[r'recommend\w*',r'collaborative filtering',r'click through',r'ctr prediction']),
 'retrieval_recommendation': dict(label_zh='检索/推荐并集', group='shared', any_of=['retrieval','recommendation']),
 'coding_software': dict(label_zh='代码/软件词汇', group='shared', patterns=[r'code',r'coding',r'programming',r'software',r'program (?:synthesis|repair|analysis|verification|generation)',r'bug\w*',r'debug\w*'], caveat='Includes conventional software work; code can also mean coding theory. Not equivalent to AI coding.'),
 'generative': dict(label_zh='生成模型词汇', group='shared', patterns=[r'generative',r'diffusion',r'gans?',r'variational autoencoders?',r'normalizing flows?',r'(?:image|video|text|audio|speech|3d|motion|molecule|molecular|code) (?:generation|synthesis)',r'text to (?:image|video|3d|audio)'], caveat='Diffusion and code/speech synthesis can have non-modern-generative-model meanings.'),
 'diffusion': dict(label_zh='扩散词汇', group='shared', patterns=[r'diffusion'], caveat='All explicit diffusion mentions, including graph/network diffusion; not a validated diffusion-model census.'),
 'multimodal': dict(label_zh='多模态/跨模态词汇', group='shared', patterns=[r'multi ?modal\w*',r'cross modal\w*',r'vision language',r'language vision',r'image text',r'text image',r'video language',r'language video',r'visual language',r'vlms?',r'mllms?']),
 'efficiency': dict(label_zh='效率/压缩/加速词汇', group='shared', patterns=[r'efficien\w*',r'compress\w*',r'quantiz\w*',r'quanti[sz]ation',r'prun\w*',r'accelerat\w*',r'low latency',r'low rank',r'distill\w*'], caveat='Cross-field efficiency vocabulary. Not automatically AI work or realized speedup.'),
 'inference_serving_gpu': dict(label_zh='推理服务/GPU基础设施词汇', group='shared', patterns=[r'gpus?',r'tpus?',r'cuda',r'tensor cores?',r'kv cach\w*',r'key value cach\w*',r'model serving',r'llm serving',r'inference serving',r'inference engines?',r'inference system\w*',r'inference accelerat\w*',r'neural network inference',r'llm inference',r'language model inference',r'model inference'], caveat='Does not count bare statistical inference, generic training or generic memory.'),
 'theory_optimization': dict(label_zh='理论/优化词汇', group='shared', patterns=[r'theor\w*',r'optimi[sz]\w*',r'convergen\w*',r'convex\w*',r'gradient\w*',r'regret',r'generalization',r'generalisation',r'sample complexity',r'pac bayes\w*',r'lower bounds?',r'upper bounds?'], caveat='Includes optimizer/optimization mentions in applications; does not measure all theory.'),
 'evaluation': dict(label_zh='评估/基准词汇', group='shared', patterns=[r'evaluat\w*',r'benchmarks?',r'benchmarking',r'assess\w*',r'measur\w*'], caveat='Includes conventional measurement papers and measurement terminology.'),
 'safety_security': dict(label_zh='安全/公平/隐私/稳健性词汇', group='shared', patterns=[r'safety',r'safe',r'secur\w*',r'privacy',r'private',r'fair\w*',r'(?:social|demographic|gender|racial) bias\w*',r'robust\w*',r'hallucinat\w*',r'jailbreak\w*',r'toxic\w*',r'attack\w*',r'trustworth\w*',r'vulnerab\w*'], caveat='Broad cross-field signal including conventional robustness, fairness and security. Bare bias/alignment excluded to avoid inductive-bias/geometric-alignment conflation.'),
 'evaluation_safety': dict(label_zh='评估/安全词汇并集', group='shared', any_of=['evaluation','safety_security']),
 'traditional_statistics': dict(label_zh='统计/概率传统方法词汇', group='specialty', patterns=[r'bayesian',r'gaussian processes?',r'kernels?',r'causal\w*',r'causality',r'statistic\w*',r'probabilistic',r'markov',r'monte carlo']),
 'rl_control': dict(label_zh='强化学习/控制词汇', group='specialty', patterns=[r'reinforcement learning',r'bandits?',r'policy (?:gradient|optimi[sz]ation|learning)',r'markov decision',r'control(?:ler|lers)?',r'robot\w*']),
 'graphs': dict(label_zh='图/网络学习词汇', group='specialty', patterns=[r'graphs?',r'knowledge graphs?',r'graph neural networks?'], caveat='Graph vocabulary can include graph algorithms beyond ML.'),
 'nlp_translation_syntax': dict(label_zh='机器翻译/句法分析词汇', group='specialty', patterns=[r'translation',r'parsing',r'syntax',r'syntactic',r'part of speech',r'dependency pars\w*']),
 'nlp_extraction_qa': dict(label_zh='信息抽取/问答词汇', group='specialty', patterns=[r'question answering',r'information extraction',r'named entity',r'relation extraction',r'event extraction',r'coreference']),
 'vision_recognition_detection': dict(label_zh='视觉识别/检测/分割词汇', group='specialty', patterns=[r'recognition',r'object detection',r'object detector\w*',r'segmentation',r'image classification'], caveat='Recognition/segmentation also occur outside vision; title wording proxy.'),
 'vision_geometry_rendering': dict(label_zh='三维/几何/渲染词汇', group='specialty', patterns=[r'3d',r'point clouds?',r'depth estimation',r'pose estimation',r'multi view',r'stereo',r'nerf\w*',r'neural radiance',r'render\w*',r'gaussian splatting']),
 'software_testing_analysis': dict(label_zh='软件测试/分析/修复词汇', group='specialty', patterns=[r'testing',r'test generation',r'test suites?',r'fuzz\w*',r'static analysis',r'dynamic analysis',r'program analysis',r'program repair',r'bug\w*',r'debug\w*',r'verification']),
 'systems_storage_networking': dict(label_zh='存储/网络/分布式系统词汇', group='specialty', patterns=[r'storage',r'file systems?',r'filesystem\w*',r'cach\w*',r'databases?',r'transactions?',r'consensus',r'distributed systems?',r'networking',r'computer networks?',r'network (?:stack|protocol|traffic|packet|switch)\w*',r'data ?center networks?',r'rdma',r'virtualization',r'operating systems?',r'cpu\w*'], caveat='Cache vocabulary may refer to model caches. Bare network(s) excluded to avoid neural-network conflation. No mutually exclusive traditional/AI split.'),
 'mining_temporal_anomaly': dict(label_zh='数据挖掘/时序/异常任务词汇', group='specialty', patterns=[r'data mining',r'clustering',r'anomaly',r'outlier\w*',r'time series',r'temporal',r'forecast\w*'])
}

def norm(text):
    return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKC',text).casefold()).strip()
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvout(path,rows,fields=None):
    rows=list(rows)
    fields=fields or list(rows[0]) if rows else (fields or [])
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def classify(text, rules, compiled):
    direct={}
    for name,patterns in compiled.items():
        spans=set()
        for pat in patterns:
            for m in pat.finditer(text):spans.add((m.start(),m.end(),m.group()))
        if spans: direct[name]=[dict(start=a,end=b,text=t) for a,b,t in sorted(spans)]
    result={}; pending=set(rules)
    while pending:
        progress=False
        for name in sorted(pending):
            r=rules[name];deps=r.get('any_of',[])+r.get('all_of',[])
            if any(d in pending for d in deps):continue
            hit=bool(direct.get(name)) or any(d in result for d in r.get('any_of',[]))
            if r.get('all_of'):hit=all(d in result for d in r['all_of'])
            if hit:
                evidence=list(direct.get(name,[]))
                for d in deps:
                    if d in result:evidence.extend(result[d]['spans'])
                unique={(s['start'],s['end'],s['text']) for s in evidence}
                result[name]={'spans':[dict(start=a,end=b,text=t) for a,b,t in sorted(unique)],'components':[d for d in deps if d in result]}
            pending.remove(name);progress=True
        if not progress:raise ValueError('Cyclic or missing rule dependency')
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--input',type=Path,action='append',dest='inputs')
    ap.add_argument('--rules',type=Path,help='Optional alternate JSON rules; default rules embedded')
    ap.add_argument('--skip-paper-audit',action='store_true',help='Skip large paper-level matched-spans file')
    a=ap.parse_args();out=a.output or a.root/'comparison';out.mkdir(parents=True,exist_ok=True)
    rules=json.loads(a.rules.read_text(encoding='utf-8')) if a.rules else RULES
    # A custom rules file can be either the rule mapping or the exported envelope.
    if 'rules' in rules:rules=rules['rules']
    compiled={k:[re.compile(r'\b(?:'+p+r')\b') for p in r.get('patterns',[])] for k,r in rules.items()}
    sources=a.inputs or [a.root/p for p in INPUTS]
    manifest=[];papers=[];seen=set();dupes=[]
    for p in sources:
        entries=0
        with p.open(encoding='utf-8-sig') as f:
            for ln,line in enumerate(f,1):
                if not line.strip():continue
                x=json.loads(line);entries+=1
                venue=x.get('venue',x.get('conference'));year=int(x['year'])
                if venue not in VENUES or not 2020<=year<=2026:raise ValueError(f'Unexpected venue/year {venue}/{year} at {p}:{ln}')
                title=x['title'].strip();pid=x.get('stable_id') or x.get('paper_id') or x.get('id')
                if not title or not pid:raise ValueError(f'Missing title/ID at {p}:{ln}')
                key=(venue,year,str(pid))
                if key in seen:dupes.append(dict(venue=venue,year=year,id=pid,input=str(p),line=ln));continue
                seen.add(key)
                if x.get('main_research') is False:continue
                status='provisional_excluded' if (venue=='NeurIPS' and year==2026) or x.get('source_type')=='provisional_program_incomplete' else 'scope_break_separate' if venue=='OSDI' and year==2026 else 'source_census'
                papers.append(dict(venue=venue,year=year,paper_id=str(pid),title=title,normalized_title=norm(title),track=x.get('track',''),official_url=x.get('official_url') or x.get('url',''),source_url=x.get('source_url',''),source_type=x.get('source_type') or x.get('source_format',''),source_corpus=p.name,source_record_sha256=x.get('source_sha256',''),analysis_status=status,publication_status=x.get('publication_status','')))
        manifest.append(dict(path=str(p.resolve()),relative_path=str(p.relative_to(a.root)) if p.is_relative_to(a.root) else p.name,sha256=sha(p),bytes=p.stat().st_size,records=entries))
    # Reject duplicate IDs rather than silently changing an official source denominator.
    if dupes:dump(out/'duplicate_input_ids.json',dupes);raise ValueError('Duplicate venue/year IDs; inspect duplicate_input_ids.json')
    papers.sort(key=lambda x:(x['venue'],x['year'],x['paper_id']))
    dump(out/'source_corpus_manifest.json',dict(version=VERSION,created_utc=datetime.now(timezone.utc).isoformat(),source_files=manifest,evidence_files=[dict(path=p,sha256=sha(a.root/p)) for p in EVIDENCE if (a.root/p).is_file()],script_sha256=sha(Path(__file__)),total_records=len(papers),normalization='NFKC + casefold + replace all non-ASCII letters/digits with spaces; collapse/strip spaces',match_span_coordinates='0-based half-open indices in normalized_title; original title preserved',no_network=True))
    dump(out/'common_topic_rules.json',dict(version=VERSION,text_field='title only',nonexclusive=True,not_exhaustive=True,rules=rules))
    with (out/'normalized_title_corpus.jsonl').open('w',encoding='utf-8') as f:
        for x in papers:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    print(f'Normalized {len(papers):,} records; source hashes and rules saved.',flush=True)
    groups=collections.defaultdict(list);n=collections.Counter();c=collections.Counter();examples=collections.defaultdict(list);tagset_counter=collections.Counter()
    audit=(out/'paper_topic_matches.jsonl').open('w',encoding='utf-8') if not a.skip_paper_audit else None
    for i,x in enumerate(papers):
        tags=classify(x['normalized_title'],rules,compiled);k=(x['venue'],x['year']);n[k]+=1
        tagset_counter['with_any_rule']+=bool(tags)
        for t,e in tags.items():
            c[k+(t,)]+=1
            if x['year'] in (2020,2025,2026) and len(examples[k+(t,)])<2:
                examples[k+(t,)].append(dict(title=x['title'],paper_id=x['paper_id'],official_url=x['official_url'],normalized_spans=e['spans']))
        if audit:audit.write(json.dumps(dict(venue=x['venue'],year=x['year'],paper_id=x['paper_id'],title=x['title'],normalized_title=x['normalized_title'],matches=tags),ensure_ascii=False,separators=(',',':'))+'\n')
        groups[k].append(x)
        if (i+1)%20000==0:print(f'Classified {i+1:,}...',flush=True)
    if audit:audit.close()
    coverage=[]
    for v in VENUES:
        for y in range(2020,2027):
            rows=groups[(v,y)];status=rows[0]['analysis_status'] if rows else 'no_edition' if v=='SOSP' and y in (2020,2022) else 'missing_input'
            note='Title-only; main/research source census; accepted list is not identical to published census.'
            if v=='NeurIPS' and y==2026:note='Incomplete pre-conference program; excluded from all trend deltas/panels.'
            if v=='OSDI' and y==2026:note='117 research only; 19 new Operational Systems omitted. Acceptance/format/scope changes remain; separate endpoint.'
            if v=='SIGIR' and y==2026:note='233 listed full papers versus 234 stated; preliminary acceptance list.'
            if v=='CVPR' and y==2026:note='4042 indexed papers versus 4089 announced acceptances; cause unknown.'
            if status=='no_edition':note='No edition. Missing calendar cell, NOT zero topical activity.'
            coverage.append(dict(venue=v,year=y,n_records=len(rows) if rows else '',analysis_status=status,in_fixed_basket_2020_2025=v in BASKET and y<=2025,notes=note))
    csvout(out/'coverage_common.csv',coverage);dump(out/'coverage_common.json',coverage)
    csvout(out/'source_urls_by_venue_year.csv',[dict(venue=v,year=y,n_records=n[v,y],source_url=url) for (v,y),rs in sorted(groups.items()) for url in sorted(set(r['source_url'] for r in rs))])
    per=[]
    for (v,y),den in sorted(n.items()):
        for t in rules:per.append(dict(venue=v,year=y,topic=t,label_zh=rules[t]['label_zh'],count=c[v,y,t],denominator=den,share=c[v,y,t]/den,share_pct=100*c[v,y,t]/den,analysis_status=groups[v,y][0]['analysis_status']))
    csvout(out/'venue_year_topic_counts.csv',per)
    dump(out/'venue_year_topic_counts.json',per)
    panels=[]
    for y in range(2020,2026):
        if any(n[v,y]==0 for v in BASKET):raise ValueError(f'Incomplete fixed basket in {y}')
        den=sum(n[v,y] for v in BASKET)
        for t in rules:
            count=sum(c[v,y,t] for v in BASKET)
            panels.append(dict(panel='fixed_nine_venues',year=y,topic=t,venue_count=len(BASKET),count=count,denominator=den,observed_paper_weighted_share_pct=100*count/den,equal_venue_weight_share_pct=sum(100*c[v,y,t]/n[v,y] for v in BASKET)/len(BASKET)))
    csvout(out/'fixed_basket_2020_2025.csv',panels);dump(out/'fixed_basket_2020_2025.json',panels)
    deltas=[];decomp=[];venue_decomp=[]
    for t in rules:
        for y0,y1 in [(2020,2025)]+[(y,y+1) for y in range(2020,2025)]:
            N0=sum(n[v,y0] for v in BASKET);N1=sum(n[v,y1] for v in BASKET)
            total=100*(sum(c[v,y1,t] for v in BASKET)/N1-sum(c[v,y0,t] for v in BASKET)/N0)
            within=0;composition=0
            for v in BASKET:
                w0=n[v,y0]/N0;w1=n[v,y1]/N1;p0=c[v,y0,t]/n[v,y0];p1=c[v,y1,t]/n[v,y1]
                wi=100*(w0+w1)/2*(p1-p0);co=100*(p0+p1)/2*(w1-w0);within+=wi;composition+=co
                if (y0,y1)==(2020,2025):venue_decomp.append(dict(topic=t,venue=v,from_year=y0,to_year=y1,within_venue_contribution_pp=wi,venue_weight_contribution_pp=co,weight_2020=w0,weight_2025=w1,share_2020_pct=100*p0,share_2025_pct=100*p1))
            decomp.append(dict(topic=t,from_year=y0,to_year=y1,observed_pooled_change_pp=total,within_venue_component_pp=within,changing_venue_weights_component_pp=composition,residual_pp=total-within-composition))
        p0=next(p for p in panels if p['year']==2020 and p['topic']==t);p1=next(p for p in panels if p['year']==2025 and p['topic']==t)
        deltas.append(dict(topic=t,label_zh=rules[t]['label_zh'],count_2020=p0['count'],n_2020=p0['denominator'],count_2025=p1['count'],n_2025=p1['denominator'],pooled_2020_pct=p0['observed_paper_weighted_share_pct'],pooled_2025_pct=p1['observed_paper_weighted_share_pct'],pooled_delta_pp=p1['observed_paper_weighted_share_pct']-p0['observed_paper_weighted_share_pct'],equal_venue_2020_pct=p0['equal_venue_weight_share_pct'],equal_venue_2025_pct=p1['equal_venue_weight_share_pct'],equal_venue_delta_pp=p1['equal_venue_weight_share_pct']-p0['equal_venue_weight_share_pct']))
    csvout(out/'fixed_basket_headline_deltas.csv',deltas);dump(out/'fixed_basket_headline_deltas.json',deltas)
    csvout(out/'change_decomposition.csv',decomp);csvout(out/'change_decomposition_by_venue.csv',venue_decomp)
    pairs=[];scopebreak=[];history=[]
    for v in VENUES:
        for y0,y1 in [(2020,2025),(2025,2026)]:
            if v=='NeurIPS' and y1==2026:continue
            if not n[v,y0] or not n[v,y1]:continue
            target=scopebreak if v=='OSDI' and y1==2026 else pairs if y1==2026 else history
            for t in rules:
                target.append(dict(venue=v,topic=t,from_year=y0,to_year=y1,count_from=c[v,y0,t],n_from=n[v,y0],share_from_pct=100*c[v,y0,t]/n[v,y0],count_to=c[v,y1,t],n_to=n[v,y1],share_to_pct=100*c[v,y1,t]/n[v,y1],change_pp=100*(c[v,y1,t]/n[v,y1]-c[v,y0,t]/n[v,y0]),analysis_status='scope_break_separate' if target is scopebreak else 'paired_same_venue'))
    csvout(out/'paired_2025_2026.csv',pairs);csvout(out/'osdi_2026_scopebreak_separate.csv',scopebreak);csvout(out/'venue_2020_2025_deltas.csv',history)
    # Count and export overlap contrasts, including broad versus strict agents and pretraining usage.
    contrast_topics=['modern_foundation_llm','historical_pretrained','modern_or_historical','agents_broad','agents_language_action_strict','pretraining_explicit','pretrained_usage_cue','posttraining_named_broad','posttraining_model_context','reasoning','testtime_compute']
    csvout(out/'key_definition_sensitivities.csv',[r for r in per if r['topic'] in contrast_topics])
    dump(out/'illustrative_title_examples.json',[dict(venue=v,year=y,topic=t,selection='first two by stable paper ID; illustrative, not precision audit or importance ranking',examples=e) for (v,y,t),e in sorted(examples.items())])
    # Deterministic audit sample: at most 6 matched records per topic from each time band.
    # Full evidence is in paper_topic_matches.jsonl; no precision/recall estimates are claimed.
    validation=dict(version=VERSION,total_records=len(papers),distinct_venue_year_ids=len(seen),duplicate_ids=len(dupes),title_only=True,all_topics_nonexclusive=True,fixed_basket=BASKET,fixed_basket_2020_n=sum(n[v,2020] for v in BASKET),fixed_basket_2025_n=sum(n[v,2025] for v in BASKET),provisional_excluded_n=n['NeurIPS',2026],scope_break_osdi_2026_n=n['OSDI',2026],no_edition_cells=[['SOSP',2020],['SOSP',2022]],decomposition_max_abs_residual_pp=max(abs(d['residual_pp']) for d in decomp),classification_validation='Regex behavior and denominator checks only; no human semantic precision/recall benchmark',output_rule_sha256=sha(out/'common_topic_rules.json'))
    assert validation['decomposition_max_abs_residual_pp']<1e-10
    assert all(r['count']<=r['denominator'] for r in per)
    assert all(c[v,y,'agents_language_action_strict']<=c[v,y,'agents_broad'] for v,y in n)
    assert all(c[v,y,'posttraining_model_context']<=c[v,y,'posttraining_named_broad'] for v,y in n)
    dump(out/'validation.json',validation)
    print(json.dumps(validation,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
