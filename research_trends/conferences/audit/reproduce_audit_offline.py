#!/usr/bin/env python3
"""Reproduce the frozen sample and label statistics from the packaged frame, offline."""
from pathlib import Path
import argparse,json,gzip,hashlib,random,subprocess,sys,shutil,csv,collections

def main():
 p=Path(__file__).resolve().parent
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=p/'reproduced');a=ap.parse_args()
 if a.output.resolve()==p:raise SystemExit('Choose a separate output directory; frozen source files must remain intact.')
 if a.output.exists() and any(a.output.iterdir()):raise SystemExit('Output must be new or empty; refusing to overwrite earlier work.')
 b=gzip.decompress((p/'sampling_frame.jsonl.gz').read_bytes());fm=json.loads((p/'sampling_frame_manifest.json').read_text(encoding='utf-8'))
 if hashlib.sha256(b).hexdigest()!=fm['uncompressed_sha256']:raise SystemExit('Sampling frame checksum mismatch')
 frame=[json.loads(l) for l in b.splitlines() if l.strip()];m=json.loads((p/'sampling_manifest.json').read_text(encoding='utf-8'));sample=[]
 for st in m['strata']:
  positive=[r for r in frame if r['stratum']==st['stratum']]
  eligible=sorted((r for r in positive if r['abstract'].strip()),key=lambda r:(r['venue'],r['year'],r['paper_id']))
  assert len(positive)==st['lexical_positive_papers'] and len(eligible)==st['eligible_abstract_papers']
  n=st['sample_n'];N=len(eligible)
  selected=sorted(random.Random(str(m['seed'])+':'+st['stratum']).sample(eligible,n),key=lambda r:(r['venue'],r['year'],r['paper_id']))
  for r in selected:
   sample.append(dict(audit_id=f'A{len(sample)+1:02}',stratum=r['stratum'],paper_id=r['paper_id'],venue=r['venue'],year=r['year'],title=r['title'],abstract=r['abstract'],paper_url=r['paper_url'],source_url=r['source_url'],matched_title_terms=r['matched_title_terms'],stratum_eligible_N=N,stratum_sample_n=n,inclusion_probability=n/N,inverse_probability_weight=N/n))
 expected=json.loads((p/'audit_sample_unlabeled.json').read_text(encoding='utf-8'))
 assert sample==expected, 'Sample differs from frozen 60 records'
 a.output.mkdir(parents=True,exist_ok=True)
 (a.output/'audit_sample_unlabeled.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
 with (a.output/'audit_sample_unlabeled.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=sample[0]);w.writeheader();w.writerows(sample)
 for fn in ['sampling_manifest.json','label_agent_abstracts_portable.py']:shutil.copyfile(p/fn,a.output/fn)
 subprocess.run([sys.executable,'-X','utf8',str(a.output/'label_agent_abstracts_portable.py')],check=True,stdout=subprocess.DEVNULL)
 checks={}
 for fn in ['audit_sample_unlabeled.json','agent_abstract_audit.json','audit_summary.json']:
  checks[fn]=json.loads((p/fn).read_text(encoding='utf-8'))==json.loads((a.output/fn).read_text(encoding='utf-8'))
 for fn in ['agent_abstract_audit.csv','audit_stratum_summary.csv']:
  with (p/fn).open(encoding='utf-8',newline='') as f, (a.output/fn).open(encoding='utf-8',newline='') as g:checks[fn]=list(csv.DictReader(f))==list(csv.DictReader(g))
 assert all(checks.values()),checks
 result={'result':'PASS','offline':True,'third_party_dependencies':False,'frame_rows':len(frame),'eligible_rows':sum(bool(r['abstract'].strip()) for r in frame),'sample_n':len(sample),'semantic_equality_checks':checks,'note':'Frozen AI decisions are replayed; no fresh AI/human annotation, new network evidence or recall estimation.'}
 (a.output/'portable_reproduction_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
