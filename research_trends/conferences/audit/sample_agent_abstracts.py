#!/usr/bin/env python3
"""Reproduce the title-positive, available-abstract stratified sample; offline only."""
import json,re,random,hashlib,csv
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
SEED=20261009
STRATA=[('ML_2020_2022','ML',[2020,2021,2022],16),('ML_2024_2026','ML',[2024,2025,2026],17),('ACL_2020_2022','ACL',[2020,2021,2022],11),('ACL_2024_2026','ACL',[2024,2025,2026],16)]
SOURCES={'ML':ROOT/'ml/metadata_main.jsonl','ACL':ROOT/'nlp_vision/acl_main.jsonl'}
pattern=json.load(open(ROOT/'ml/title_topic_rules.json'))['rules']['agents_tools_memory']['pattern']
regex=re.compile(pattern,re.I)
sources={g:[json.loads(l) for l in open(p)] for g,p in SOURCES.items()}
excluded_provisional=[r for r in sources['ML'] if r['venue']=='NeurIPS' and int(r['year'])==2026]
sources['ML']=[r for r in sources['ML'] if not(r['venue']=='NeurIPS' and int(r['year'])==2026)]
sample=[];frame=[];by_year=[]
for sid,group,years,n in STRATA:
 rows=[r for r in sources[group] if int(r['year']) in years]
 positives=[r for r in rows if regex.search(r['title'])]
 eligible=sorted((r for r in positives if str(r.get('abstract','')).strip()),key=lambda r:(r['venue'],int(r['year']),r.get('paper_id',r.get('stable_id',''))))
 rng=random.Random(f'{SEED}:{sid}')
 selected=sorted(rng.sample(eligible,n),key=lambda r:(r['venue'],int(r['year']),r.get('paper_id',r.get('stable_id',''))))
 N=len(eligible)
 frame.append(dict(stratum=sid,conference_group=group,years=years,all_papers=len(rows),all_papers_with_abstract=sum(bool(str(r.get('abstract','')).strip()) for r in rows),lexical_positive_papers=len(positives),eligible_abstract_papers=N,missing_abstract_positive_papers=len(positives)-N,abstract_coverage_among_positive=N/len(positives),sample_n=n,inclusion_probability=n/N,inverse_probability_weight=N/n))
 for venue,year in sorted({(r['venue'],int(r['year'])) for r in rows}):
  yr=[r for r in rows if r['venue']==venue and int(r['year'])==year]; po=[r for r in positives if r['venue']==venue and int(r['year'])==year]
  by_year.append(dict(stratum=sid,venue=venue,year=year,all_papers=len(yr),all_with_abstract=sum(bool(str(r.get('abstract','')).strip()) for r in yr),lexical_positive_papers=len(po),positive_with_abstract=sum(bool(str(r.get('abstract','')).strip()) for r in po)))
 for r in selected:
  sample.append(dict(audit_id=f'A{len(sample)+1:02}',stratum=sid,paper_id=r.get('paper_id',r.get('stable_id')),venue=r['venue'],year=int(r['year']),title=r['title'],abstract=r['abstract'],paper_url=r['official_url'],source_url=r.get('source_url',''),matched_title_terms=[m.group() for m in regex.finditer(r['title'])],stratum_eligible_N=N,stratum_sample_n=n,inclusion_probability=n/N,inverse_probability_weight=N/n))
manifest=dict(title_rule_file_sha256=hashlib.sha256((ROOT/'ml/title_topic_rules.json').read_bytes()).hexdigest(),excluded_provisional_neurips_2026=dict(all_papers=len(excluded_provisional),lexical_positive_papers=sum(bool(regex.search(r['title'])) for r in excluded_provisional),positive_with_abstract=sum(bool(regex.search(r['title'])) and bool(str(r.get('abstract','')).strip()) for r in excluded_provisional)),seed=SEED,random_generator='Python random.Random(str(seed)+":"+stratum); sample without replacement; sorted eligible population by venue, year, stable paper ID',python_version=__import__('sys').version,pattern=pattern,source_sha256={g:hashlib.sha256(p.read_bytes()).hexdigest() for g,p in SOURCES.items()},strata=frame,by_venue_year=by_year,population_restriction='Observed main-conference records, ML (ICLR/ICML/NeurIPS) and ACL, 2020–2022 or 2024–2026, matching broad agent/tool/memory title regex, with nonempty collected abstract. Excludes 2023, CVPR, title-negative papers, missing abstracts, and all NeurIPS 2026 records because their observed program is incomplete. ICML/ICLR/ACL 2026 remain included as collected; upstream source and track caveats apply.',allocation='Near-balanced four-stratum sample. ACL 2020–2022 has only 11 eligible papers, all sampled; remaining 49 allocated ML early 16, ML recent 17, ACL recent 16. Allocation fixed before abstract interpretation.',audit_type='AI-assisted single-rater title-and-abstract content audit; not human validation and not recall estimation.')
(OUT/'sampling_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'audit_sample_unlabeled.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2))
with open(OUT/'audit_sample_unlabeled.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=sample[0].keys());w.writeheader();w.writerows(sample)
with open(OUT/'stratum_frame.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=frame[0].keys());w.writeheader();w.writerows(frame)
print(json.dumps({'sample_n':len(sample),'strata':frame},ensure_ascii=False,indent=2))
