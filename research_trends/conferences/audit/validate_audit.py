#!/usr/bin/env python3
import json,hashlib,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
fns=['audit_sample_unlabeled.json','agent_abstract_audit.json','agent_abstract_audit.csv','audit_summary.json','audit_stratum_summary.csv','sampling_manifest.json']
before={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in fns}
subprocess.run(['python',str(p/'sample_agent_abstracts.py')],stdout=subprocess.DEVNULL,check=True)
subprocess.run(['python',str(p/'label_agent_abstracts.py')],stdout=subprocess.DEVNULL,check=True)
a=json.load(open(p/'agent_abstract_audit.json'));s=json.load(open(p/'audit_sample_unlabeled.json'));m=json.load(open(p/'sampling_manifest.json'));summary=json.load(open(p/'audit_summary.json'));compact=json.load(open(p/'audit_compact_transfer.json'))
checks={'sample_n':len(a),'unique_paper_ids':len({r['paper_id'] for r in a}),'all_nonempty_abstracts':all(r['abstract'].strip() for r in s),'no_neurips_2026':all(not(r['venue']=='NeurIPS' and r['year']==2026) for r in a),'exact_quote_substrings':all(x['evidence_quote'] in y['abstract'] for x,y in zip(a,s)),'all_quotes_max25_words':all(len(r['evidence_quote'].split())<=25 for r in a),'all_https_paper_urls':all(r['paper_url'].startswith('https://') for r in a),'positive_probabilities':all(0<r['inclusion_probability']<=1 for r in a),'inverse_probability_weights_correct':all(abs(r['inclusion_probability']*r['inverse_probability_weight']-1)<1e-10 for r in a),'weights_sum_to_eligible_population':abs(sum(r['inverse_probability_weight'] for r in a)-sum(x['eligible_abstract_papers'] for x in m['strata']))<1e-8,'finite_population_corrections_correct':all(abs(h['finite_population_correction']-(1-h['sample_n']/h['eligible_abstract_papers']))<1e-12 for h in summary['strata']),'census_ci_collapses':all(h['strict_hypergeom95_fraction_low']==h['strict_hypergeom95_fraction_high']==h['strict_central_sample_fraction'] for h in summary['strata'] if h['sample_n']==h['eligible_abstract_papers']),'compact_summary_matches':compact['summary']==summary,'compact_source_manifest_matches':compact['sampling_manifest']==m,'compact_all60_records_match':all(all(r[k]==c[k] for k in c) for r,c in zip(a,compact['papers'])) and len(compact['papers'])==60,'compact_under80kb':(p/'audit_compact_transfer.json').stat().st_size<80000,'reproduced_files_identical':{f:before[f]==hashlib.sha256((p/f).read_bytes()).hexdigest() for f in fns}}
checks['all_main_checks_pass']=checks['sample_n']==60 and checks['unique_paper_ids']==60 and all(v for k,v in checks.items() if isinstance(v,bool)) and all(checks['reproduced_files_identical'].values())
(p/'validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps(checks,indent=2))
assert checks['all_main_checks_pass']
