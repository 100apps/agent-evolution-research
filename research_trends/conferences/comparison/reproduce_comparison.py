#!/usr/bin/env python3
"""Reproduce unified statistics from the three exact existing corpora; no network."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=Path(__file__).resolve().parent
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=p.parent,help='conferences directory containing the three corpora');ap.add_argument('--output',type=Path,default=p/'reproduced');a=ap.parse_args()
 if a.output.exists() and any(a.output.iterdir()):raise SystemExit('Output must be new or empty; refusing to overwrite earlier work.')
 m=json.loads((p/'source_corpus_manifest.json').read_text(encoding='utf-8'))
 problems=[]
 for r in m['source_files']:
  path=a.root/r['relative_path']
  if not path.is_file():problems.append('Missing: '+r['relative_path'])
  elif sha(path)!=r['sha256']:problems.append('Source snapshot differs: '+r['relative_path'])
 if problems:raise SystemExit('\n'.join(problems)+'\nRestore the base archives and run systems_ir/restore_metadata.py first. Never relabel a new snapshot as the frozen result.')
 subprocess.run([sys.executable,'-X','utf8',str(p/'compare_titles.py'),'--root',str(a.root),'--output',str(a.output),'--rules',str(p/'common_topic_rules.json'),'--skip-paper-audit'],check=True)
 expected=json.loads((p/'reproduction_validation.json').read_text(encoding='utf-8'))
 checks=[]
 for r in expected['checks']:
  q=a.output/r['file']; checks.append({'file':r['file'],'byte_identical':q.is_file() and sha(q)==r['sha256']})
 if not all(r['byte_identical'] for r in checks):raise SystemExit('Reproduction mismatch: '+json.dumps(checks))
 result={'result':'PASS','files_verified':len(checks),'checks':checks,'note':'Source manifest timestamp and local paths are deliberately not byte-compared. The 55 MB normalized corpus is regenerated but not shipped; large per-paper match detail was skipped.'}
 (a.output/'addon_reproduction_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
