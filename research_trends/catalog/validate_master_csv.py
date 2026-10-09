#!/usr/bin/env python3
"""Independent streaming acceptance gate for the released CSV and its evidence."""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
from schema_validation import SCHEMA,validate_master_schema,validate_source_coverage_row

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--master',type=Path,required=True)
 ap.add_argument('--coverage-manifest',type=Path,required=True)
 ap.add_argument('--citation-audit',type=Path)
 args=ap.parse_args()
 audits={}
 if args.citation_audit:
  for line in args.citation_audit.read_text(encoding='utf8').splitlines():
   a=json.loads(line)
   if a['http_status']==200:audits[a['query_sha256']]=a
 expected=[f['name'] for f in SCHEMA['fields']]
 seen=set();counts=Counter();errors=[]
 with args.master.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  if reader.fieldnames[:len(expected)]!=expected:raise ValueError('first 61 columns differ from frozen schema')
  for number,raw in enumerate(reader,2):
   row={}
   for spec in SCHEMA['fields']:
    name=spec['name'];s=raw[name];kind=spec['type']
    row[name]=json.loads(s) if kind.startswith('json_') else int(s) if kind in ('integer','integer_or_empty') and s else s
   issues=validate_master_schema(row)
   if issues:errors.append((number,issues[:3]))
   pid=row['paper_id']
   if pid in seen:errors.append((number,['duplicate paper_id']))
   seen.add(pid)
   state=raw['citation_status'];count=raw['citation_count']
   impact=json.loads(raw['impact_metrics_json'])
   if impact.get('paper_id')!=pid or impact.get('schema_version')!='paper-impact-v1.0.0-proposed':
    errors.append((number,['impact sidecar identity/schema mismatch']))
   if count:
    observations=impact.get('citation_observations') or []
    if state!='reported_exact_doi' or not count.isdigit() or not raw['citation_provider'] or not raw['citation_as_of'] or len(observations)!=1:
     errors.append((number,['citation value lacks provider/DOI evidence']))
    for observation in observations:
     source=observation.get('source') or {}
     a=audits.get(source.get('request_fingerprint'))
     if not a or a['raw_sha256']!=source.get('raw_sha256') or observation.get('value')!=int(count):
      errors.append((number,['citation raw hash unresolved']))
   elif state=='reported_exact_doi':errors.append((number,['reported status lacks count']))
   if raw['views_count'] or raw['downloads_count']:
    errors.append((number,['article-level usage values require an observed provider in impact JSON']))
   counts['rows']+=1;counts['citations:'+state]+=1
   counts['candidate']+=bool(row['category_ids_l3_json'])
   counts['authors']+=bool(row['authors_json'])
   counts['paper_institutions']+=bool(row['publication_affiliations_json'])
   counts['countries']+=bool(row['countries_json'])
   if len(errors)>10:break
 with args.coverage_manifest.open(encoding='utf-8-sig',newline='') as f:
  coverage=list(csv.DictReader(f))
 for row in coverage:
  if issues:=validate_source_coverage_row(row):errors.append(('coverage',issues))
 if counts['rows']!=89530 or len(coverage)!=70:errors.append(('inventory',['expected 89530 records and 70 source-year coverage rows']))
 result={'passed':not errors,'master_sha256':sha(args.master),'rows':counts['rows'],
         'columns':len(reader.fieldnames or []),'source_coverage_rows':len(coverage),
         'counts':dict(counts),'errors':errors[:10]}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)

if __name__=='__main__':main()
