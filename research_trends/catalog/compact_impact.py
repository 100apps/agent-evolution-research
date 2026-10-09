#!/usr/bin/env python3
"""Keep 61 frozen master fields and eight compact impact/usage columns."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json
from collections import Counter
from pathlib import Path
from schema_validation import SCHEMA

BASE=[x['name'] for x in SCHEMA['fields']]
EXTRA=['citation_count','citation_provider','citation_as_of','citation_status',
       'publication_age_days','impact_metrics_json','views_count','downloads_count']

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def source(provider,record_id=None,url=None,at=None,raw=None,fingerprint=None,match='not_joined',identifier=None):
 return {'provider':provider,'record_id':record_id,'source_url':url,'retrieved_at':at,
         'provider_updated_at':None,'raw_sha256':raw,'raw_field':None,
         'request_fingerprint':fingerprint,'identifier_match':match,'matched_identifier':identifier}

def state(status,reason,attempted=None):
 return {'status':status,'missing_reason':reason,'attempted_at':attempted}

def impact(row,audits):
 pid=row['paper_id'];count=row['citation_count'];cs=row['citation_status']
 age_source=source('frozen_conference_metadata',url=row['official_url'] or None,
                   at=row['retrieved_at'] or None)
 occurrence=json.loads(row['occurrences_json'])[0]
 precision=occurrence.get('date_precision') or 'unknown'
 if precision not in ('day','month','year'):precision='unknown'
 age={'days':None,'as_of':'2026-10-09','date_used':None,'date_precision':precision,
      'basis':'unknown','status':'field_missing',
      'missing_reason':'publication date is not verified at day precision',
      'source':age_source}
 objects=[]
 integrity=[]
 if count:
  evidence=json.loads(row['attention_evidence_json'])[0]
  audit=audits[evidence['query_sha256']]
  src=source('OpenAlex',record_id=evidence['provider_work_id'],url=evidence['provider_work_id'],
             at=row['citation_as_of'],raw=evidence['raw_sha256'],
             fingerprint=evidence['query_sha256'],match='exact_doi',identifier=evidence['doi'])
  src['raw_field']='cited_by_count'
  objects.append({'metric':'citation_count','value':int(count),'status':'present',
                  'missing_reason':None,'as_of':row['citation_as_of'],'unit':'citations',
                  'window':{'kind':'lifetime_to_asof','start':None,'end':row['citation_as_of'][:10],
                            'definition':'OpenAlex cited_by_count observed at retrieval; coverage may backfill'},
                  'source':src,'method_version':'exact-doi-batch-v1',
                  'caveats':['Citation coverage differs by field, publication year, and source; count is not a quality score.']})
  if row['retraction_status'] in ('openalex_reported_retracted','openalex_reported_not_retracted'):
   flag=row['retraction_status']=='openalex_reported_retracted'
   integrity.append({'kind':'retraction','assertion':'reported' if flag else 'not_flagged_by_source',
                     'notice_url':None,'notice_doi':None,'original_doi':evidence['doi'],
                     'event_date':None,'event_date_precision':'unknown',
                     'evidence_text':'OpenAlex is_retracted='+('true' if flag else 'false')+' at retrieval; no independent notice audit',
                     'source':{**src,'raw_field':'is_retracted'}})
  citation_state=state('present',None,row['citation_as_of'])
 else:
  mapping={'no_verified_doi':('missing_identifier','no exact verified DOI in saved source'),
           'ambiguous_exact_doi':('identifier_conflict','multiple OpenAlex works returned for exact DOI'),
           'possibly_truncated':('partial_response','OR batch returned more matches than page size'),
           'not_found_exact_doi':('not_found','exact DOI absent in retrieved OpenAlex response'),
           'not_collected':('not_requested','DOI batch was not requested')}
  status,reason=mapping.get(cs,('field_missing','provider did not return usable count'))
  citation_state=state(status,reason)
 return {'schema_version':'paper-impact-v1.0.0-proposed','paper_id':pid,
         'publication_age':age,'citation_observations':objects,
         'citation_counts_by_year':[],'normalized_citation_observations':[],
         'usage_observations':[],'public_reviews':[],'artifact_links':[],
         'integrity_events':integrity,
         'collection_status':{
           'citations':citation_state,
           'views':state('not_exposed','no comparable article-level view feed in current sources'),
           'downloads':state('not_exposed','no comparable article-level download feed in current sources'),
           'public_reviews':state('not_requested','review payload not collected for this record'),
           'artifacts':state('not_requested','code and data links not systematically collected'),
           'integrity':state('present',None,row['citation_as_of']) if integrity else state('not_requested','independent retraction/correction audit not completed')},
         'adapter_version':'impact-adapter-v1.0.0'}

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--master',type=Path,required=True)
 ap.add_argument('--citation-audit',type=Path,required=True)
 ap.add_argument('--output-dir',type=Path,required=True)
 args=ap.parse_args()
 output=args.output_dir.resolve()
 if output.exists() and any(output.iterdir()):raise SystemExit('output directory must be empty')
 output.mkdir(parents=True,exist_ok=True)
 audits={a['query_sha256']:a for a in map(json.loads,args.citation_audit.read_text(encoding='utf8').splitlines()) if a['http_status']==200}
 counts=Counter();dest=output/'master_papers.csv'
 with args.master.open(encoding='utf-8-sig',newline='') as inp,dest.open('w',encoding='utf-8-sig',newline='') as out:
  reader=csv.DictReader(inp)
  if reader.fieldnames[:61]!=BASE:raise ValueError('frozen 61-field schema order changed')
  writer=csv.DictWriter(out,fieldnames=BASE+EXTRA);writer.writeheader()
  for row in reader:
   obj=impact(row,audits)
   result={k:row[k] for k in BASE}
   result.update(citation_count=row['citation_count'],citation_provider=row['citation_provider'],
                 citation_as_of=row['citation_as_of'],citation_status=row['citation_status'],
                 publication_age_days='',impact_metrics_json=json.dumps(obj,ensure_ascii=False,separators=(',',':')),
                 views_count='',downloads_count='')
   writer.writerow(result)
   counts[row['citation_status']]+=1
 with dest.open('rb') as src,(output/'master_papers.csv.gz').open('wb') as sink:
  with gzip.GzipFile(filename='',mode='wb',fileobj=sink,compresslevel=9,mtime=0) as z:
   for block in iter(lambda:src.read(1<<20),b''):z.write(block)
 receipt={'rows':sum(counts.values()),'columns':len(BASE+EXTRA),'base_schema':SCHEMA['schema_version'],
          'impact_schema':'paper-impact-v1.0.0-proposed','citation_status_counts':dict(counts),
          'source_master_sha256':sha(args.master),'citation_audit_sha256':sha(args.citation_audit),
          'csv_bytes':dest.stat().st_size,'csv_sha256':sha(dest),
          'gzip_bytes':(output/'master_papers.csv.gz').stat().st_size,
          'gzip_sha256':sha(output/'master_papers.csv.gz')}
 (output/'master_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
