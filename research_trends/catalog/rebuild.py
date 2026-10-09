#!/usr/bin/env python3
"""Offline, fresh-directory rebuild of the ten-conference master and Explorer."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--output-dir',type=Path,required=True)
 ap.add_argument('--verify-existing',action='store_true',help='Recheck a completed fresh rebuild without rerunning stages')
 args=ap.parse_args()
 out=args.output_dir.resolve()
 if not args.verify_existing and out.exists() and any(out.iterdir()):raise SystemExit('output directory must be new or empty')
 out.mkdir(parents=True,exist_ok=True)
 runs=[]
 def call(label,*cmd):
  command=[sys.executable,*map(str,cmd)]
  result=subprocess.run(command,cwd=REPO,text=True,encoding='utf8',capture_output=True)
  runs.append({'label':label,'command':command,'exit_code':result.returncode,
               'stdout':result.stdout,'stderr':result.stderr})
  (out/'commands.json').write_text(json.dumps(runs,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  if result.returncode:raise SystemExit(f'{label} failed; see {out / "commands.json"}')
 if not args.verify_existing:
  call('author extraction',REPO/'research_trends/conferences/build_author_enrichment.py',
       '--output',out/'authors.csv')
  call('metadata extraction',HERE/'metadata/enrich_local_metadata.py',
       '--conferences-root',REPO/'research_trends/conferences','--output-dir',out/'metadata','--patch-only')
  call('metadata validation',HERE/'metadata/verify_outputs.py',out/'metadata')
  call('taxonomy title candidates',HERE/'classify_titles.py','--output-dir',out/'classify')
  call('61-column schema stage',HERE/'build_master_v11.py',
       '--patch',out/'metadata/metadata_patch.jsonl.gz',
       '--source-manifest',out/'metadata/source_manifest.json',
       '--assignments',out/'classify/title_assignments.csv',
       '--fallback-authors',out/'authors.csv','--output-dir',out/'schema-stage')
  call('exact DOI citation join',HERE/'apply_citations.py',
       '--master',out/'schema-stage/master_papers.csv',
       '--citation-cache',HERE/'citation_cache','--output-dir',out/'citation-stage')
  call('compact impact CSV',HERE/'compact_impact.py',
       '--master',out/'citation-stage/master_papers.csv',
       '--citation-audit',HERE/'citation_cache/query_audit.jsonl',
       '--output-dir',out/'final')
  call('independent final validation',HERE/'validate_master_csv.py',
       '--master',out/'final/master_papers.csv',
       '--coverage-manifest',out/'schema-stage/source_coverage_manifest.csv',
       '--citation-audit',HERE/'citation_cache/query_audit.jsonl')
  call('Explorer index',HERE/'build_explorer_index.py',
       '--master',out/'final/master_papers.csv',
       '--taxonomy',HERE/'taxonomy.json','--output-dir',out/'index')
 receipt=json.loads((HERE/'data/master_receipt.json').read_text(encoding='utf8'))
 index=json.loads((HERE/'index_manifest.json').read_text(encoding='utf8'))
 checks={
  'author_csv':(out/'authors.csv','9398aaee3c503bc937103fdfba8def4d99f4f729224995263b062af420671da4'),
  'metadata_patch':(out/'metadata/metadata_patch.jsonl.gz',receipt.get('metadata_patch_sha256','70e353858c901e98bc0a80732351c42261731fbae9c371f053c5a31b5bfd6425')),
  'title_assignments':(out/'classify/title_assignments.csv','f250deda72e63eabacef0afa8cda9e36fb6219b790e6445c68fb27cb58923a0f'),
  'final_csv':(out/'final/master_papers.csv',receipt['csv_sha256']),
  'final_gzip':(out/'final/master_papers.csv.gz',receipt['gzip_sha256']),
  'explorer_index':(out/'index/papers_index.jsonl.gz',index['data_sha256'])}
 observed={label:{'expected':expected,'actual':sha(path),'matches':sha(path)==expected}
           for label,(path,expected) in checks.items()}
 (out/'rebuild_receipt.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(observed,ensure_ascii=False,indent=2))
 if not all(item['matches'] for item in observed.values()):raise SystemExit('rebuild hashes differ from published snapshot')

if __name__=='__main__':main()
