#!/usr/bin/env python3
"""Stream a compact, Excel-safe browse CSV from the immutable audit master."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re
from collections import Counter
from pathlib import Path

FIELDS=(
 'paper_id','title','official_url','venue_year_pairs_json','occurrence_ids_json',
 'publication_year','year_basis','authors','authors_raw','authors_status',
 'publication_institutions','publication_institution_status','profile_institutions_unverified',
 'institution_resolution_status','countries','country_coverage_status',
 'author_affiliation_completeness','category_ids_l1_json','category_ids_l2_json',
 'category_ids_l3_json','category_paths_text','classification_status',
 'classification_label_status','review_status','classification_method',
 'classification_reason','taxonomy_version','category_evidence_refs_json',
 'citation_count','citation_provider','citation_as_of','citation_status',
 'provider_work_id','citation_query_sha256','citation_raw_sha256',
 'doi','doi_status','dedup_status','views_count','views_status',
 'downloads_count','downloads_status','code_urls_json','data_urls_json',
 'artifact_status','source_urls_json','source_ref_ids_json','audit_ref')
FORMULA=re.compile(r'^[\s\x00-\x1f]*[=+\-@]')

def j(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def safe(value: str,counts: Counter,field: str):
 if FORMULA.match(value):
  counts['formula_guard:'+field]+=1
  return "'"+value
 return value

def project(row):
 occurrences=json.loads(row['occurrences_json'])
 impact=json.loads(row['impact_metrics_json'])
 names=json.loads(row['authors_json']) or []
 paper_institutions=json.loads(row['publication_affiliations_json']) or []
 profile=json.loads(row['profile_affiliations_json']) or []
 countries=json.loads(row['countries_json']) or []
 artifacts=impact['artifact_links']
 citations=impact['citation_observations']
 citation_source=citations[0]['source'] if citations else {}
 proof=json.loads(row['field_provenance_json'])
 source_refs=sorted({e['source_ref'] for v in proof.values() if isinstance(v,dict)
                    for e in v.get('evidence',[]) if isinstance(e,dict) and e.get('source_ref')})
 category_proof=[{'category_id':e['category_id'],'rule_ids':e['rule_ids'],
                  'quote':e['quote'],'span_start':e['span_start'],'span_end':e['span_end'],
                  'source_url':e['source_url']} for e in json.loads(row['category_evidence_json'])]
 source_urls=json.loads(row['source_urls_json'])
 metadata=json.loads(row['metadata_field_status_json'])
 doi_status=(proof.get('doi') or {}).get('status') or 'missing'
 if not row['doi'] and doi_status!='missing':doi_status='reported_but_not_verified_for_export'
 values={
  'paper_id':row['paper_id'],'title':row['title'],'official_url':row['official_url'],
  'venue_year_pairs_json':j([{'venue':o['venue'],'year':o['year'],'track':o['track']} for o in occurrences]),
  'occurrence_ids_json':row['occurrence_ids_json'],
  'publication_year':row['publication_year'],'year_basis':row['year_basis'],
  'authors':'; '.join(names),'authors_raw':row['authors_raw'],
  'authors_status':'unstructured_source_text' if not names and row['authors_raw'] else metadata['authors'],
  'publication_institutions':'; '.join(paper_institutions),
  'publication_institution_status':'present_partial_or_full' if paper_institutions else 'missing',
  'profile_institutions_unverified':'; '.join(profile),
  'institution_resolution_status':row['institution_resolution_status'],
  'countries':'; '.join(countries),'country_coverage_status':row['country_coverage_status'],
  'author_affiliation_completeness':row['author_affiliation_completeness'],
  'category_ids_l1_json':row['category_ids_l1_json'],
  'category_ids_l2_json':row['category_ids_l2_json'],
  'category_ids_l3_json':row['category_ids_l3_json'],
  'category_paths_text':row['category_paths_text'],
  'classification_status':row['classification_status'],
  'classification_label_status':row['classification_label_status'],
  'review_status':row['review_status'],
  'classification_method':row['classification_method'],
  'classification_reason':row['classification_reason'],
  'taxonomy_version':row['taxonomy_version'],
  'category_evidence_refs_json':j(category_proof),
  'citation_count':row['citation_count'],'citation_provider':row['citation_provider'],
  'citation_as_of':row['citation_as_of'],'citation_status':row['citation_status'],
  'provider_work_id':citation_source.get('record_id') or '',
  'citation_query_sha256':citation_source.get('request_fingerprint') or '',
  'citation_raw_sha256':citation_source.get('raw_sha256') or '',
  'doi':row['doi'],'doi_status':doi_status,'dedup_status':row['dedup_status'],
  'views_count':row['views_count'],'views_status':impact['collection_status']['views']['status'],
  'downloads_count':row['downloads_count'],
  'downloads_status':impact['collection_status']['downloads']['status'],
  'code_urls_json':j([a['url'] for a in artifacts if a.get('kind')=='code' and a.get('url')]),
  'data_urls_json':j([a['url'] for a in artifacts if a.get('kind')=='data' and a.get('url')]),
  'artifact_status':impact['collection_status']['artifacts']['status'],
  'source_urls_json':j(source_urls),
  'source_ref_ids_json':j(source_refs),
  'audit_ref':'master_papers.csv#paper_id='+row['paper_id'],
 }
 return values

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--master',type=Path,required=True)
 ap.add_argument('--output-dir',type=Path,required=True)
 args=ap.parse_args()
 out=args.output_dir.resolve()
 if out.exists() and any(out.iterdir()):raise SystemExit('output directory must be new or empty')
 out.mkdir(parents=True,exist_ok=True)
 counts=Counter();dest=out/'browse_papers.csv'
 with args.master.open(encoding='utf-8-sig',newline='') as source,dest.open('w',encoding='utf-8-sig',newline='') as sink:
  reader=csv.DictReader(source)
  writer=csv.DictWriter(sink,fieldnames=FIELDS)
  writer.writeheader()
  for row in reader:
   view=project(row)
   writer.writerow({name:safe(view[name],counts,name) for name in FIELDS})
   counts['rows']+=1
   counts['with_citation']+=bool(row['citation_count'])
   counts['candidate']+=row['classification_label_status']=='candidate'
   counts['country_known']+=bool(json.loads(row['countries_json']))
 if counts['rows']!=89530:raise ValueError(f'expected 89530 records, got {counts["rows"]}')
 with dest.open('rb') as raw,(out/'browse_papers.csv.gz').open('wb') as zipped:
  with gzip.GzipFile(filename='',mode='wb',fileobj=zipped,compresslevel=9,mtime=0) as z:
   for block in iter(lambda:raw.read(1<<20),b''):z.write(block)
 receipt={'schema_version':'paper-browse-v1.0.0','rows':counts['rows'],'columns':len(FIELDS),
          'source_master_sha256':sha(args.master),'counts':dict(counts),
          'csv_bytes':dest.stat().st_size,'csv_sha256':sha(dest),
          'gzip_bytes':(out/'browse_papers.csv.gz').stat().st_size,
          'gzip_sha256':sha(out/'browse_papers.csv.gz')}
 (out/'browse_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
