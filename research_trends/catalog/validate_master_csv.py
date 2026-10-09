#!/usr/bin/env python3
"""Independent streaming acceptance gate for the released CSV and its evidence."""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from schema_validation import SCHEMA,validate_master_schema,validate_source_coverage_row

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def canonical_doi(value):
 s=(value or '').strip().lower()
 for prefix in ('https://doi.org/','http://doi.org/','doi:'):
  if s.startswith(prefix):s=s[len(prefix):]
 return s

def load_citation_cache(audit_path):
 """Verify raw hashes and index only values actually returned by each request."""
 cache={}
 for line in audit_path.read_text(encoding='utf8').splitlines():
  audit=json.loads(line)
  if audit['http_status']!=200:continue
  key=audit['query_sha256'];raw_path=audit_path.parent/'raw'/(key+'.json')
  if not raw_path.is_file() or sha(raw_path)!=audit['raw_sha256']:
   raise ValueError('citation cache raw response hash mismatch: '+key)
  data=json.loads(raw_path.read_text(encoding='utf8'))
  requested={canonical_doi(x) for x in parse_qs(urlsplit(audit['url']).query)['filter'][0].removeprefix('doi:').split('|')}
  works={}
  for work in data['results']:
   doi=canonical_doi(work.get('doi'))
   if doi in requested:works[(doi,work.get('id'))]=work
  cache[key]={'audit':audit,'requested':requested,'works':works}
 return cache

def verify_citation_observation(raw,observation,cache):
 """Return issues, including swapped-paper evidence with a valid raw hash."""
 source=observation.get('source') or {}
 key=source.get('request_fingerprint')
 batch=cache.get(key)
 if not batch:return ['citation query missing from verified cache']
 audit=batch['audit']
 doi=canonical_doi(raw.get('doi'))
 matched=canonical_doi(source.get('matched_identifier'))
 work_id=source.get('record_id')
 work=batch['works'].get((doi,work_id))
 issues=[]
 if not doi or doi!=matched or doi not in batch['requested']:
  issues.append('citation DOI does not match exact requested paper DOI')
 if not work:issues.append('citation work ID and DOI pair absent from raw response')
 if audit['raw_sha256']!=source.get('raw_sha256'):
  issues.append('citation raw hash mismatch')
 if observation.get('value')!=int(raw['citation_count']):
  issues.append('citation count differs from CSV')
 if work and work.get('cited_by_count')!=int(raw['citation_count']):
  issues.append('citation count differs from raw OpenAlex work')
 if source.get('provider')!='OpenAlex' or source.get('identifier_match')!='exact_doi' or source.get('raw_field')!='cited_by_count':
  issues.append('citation provider or exact-ID basis invalid')
 if raw.get('citation_as_of')!=audit['at_utc'] or source.get('retrieved_at')!=audit['at_utc']:
  issues.append('citation observation timestamp differs from audit')
 return issues

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--master',type=Path,required=True)
 ap.add_argument('--coverage-manifest',type=Path,required=True)
 ap.add_argument('--citation-audit',type=Path)
 args=ap.parse_args()
 cache=load_citation_cache(args.citation_audit) if args.citation_audit else {}
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
     errors.extend((number,[issue]) for issue in verify_citation_observation(raw,observation,cache))
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
