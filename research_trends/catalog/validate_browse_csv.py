#!/usr/bin/env python3
"""Independent stream check for browse CSV IDs, statuses, evidence refs and gzip."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re
from collections import Counter
from pathlib import Path

FORMULA=re.compile(r'^[\s\x00-\x1f]*[=+\-@]')
def digest(path,compressed=False):
 h=hashlib.sha256()
 opener=gzip.open if compressed else open
 with opener(path,'rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def safe(x):return "'"+x if FORMULA.match(x) else x

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--master',type=Path,required=True)
 ap.add_argument('--browse',type=Path,required=True)
 ap.add_argument('--gzip',type=Path,required=True)
 args=ap.parse_args()
 errors=[];counts=Counter();seen=set()
 with args.master.open(encoding='utf-8-sig',newline='') as m,args.browse.open(encoding='utf-8-sig',newline='') as b:
  source=csv.DictReader(m);view=csv.DictReader(b)
  if len(view.fieldnames or [])!=48:errors.append('expected 48 browse columns')
  for n,(full,slim) in enumerate(zip(source,view,strict=True),2):
   pid=full['paper_id']
   if slim['paper_id']!=pid or pid in seen:errors.append(f'{n}: paper ID mismatch/duplicate')
   seen.add(pid)
   for field in ('title','official_url','publication_year','year_basis','occurrence_ids_json',
                 'category_ids_l1_json','category_ids_l2_json','category_ids_l3_json',
                 'category_paths_text','classification_status','classification_label_status',
                 'review_status','classification_method','classification_reason','taxonomy_version',
                 'citation_count','citation_provider','citation_as_of','citation_status','doi',
                 'dedup_status','country_coverage_status','author_affiliation_completeness',
                 'institution_resolution_status','views_count','downloads_count','authors_raw'):
    if slim[field]!=safe(full[field]):errors.append(f'{n}: {field} differs from master')
   occ=json.loads(full['occurrences_json'])
   expected=[{'venue':o['venue'],'year':o['year'],'track':o['track']} for o in occ]
   if json.loads(slim['venue_year_pairs_json'])!=expected:errors.append(f'{n}: venue/year pairs changed')
   if slim['authors']!=safe('; '.join(json.loads(full['authors_json']) or [])):errors.append(f'{n}: authors changed')
   if slim['publication_institutions']!=safe('; '.join(json.loads(full['publication_affiliations_json']) or [])):
    errors.append(f'{n}: publication institutions changed')
   if slim['countries']!=safe('; '.join(json.loads(full['countries_json']) or [])):
    errors.append(f'{n}: country field changed')
   impact=json.loads(full['impact_metrics_json'])
   if slim['views_status']!=impact['collection_status']['views']['status'] or slim['downloads_status']!=impact['collection_status']['downloads']['status']:
    errors.append(f'{n}: usage missing status changed')
   evidence=json.loads(slim['category_evidence_refs_json'])
   if len(evidence)!=len(json.loads(full['category_evidence_json'])):errors.append(f'{n}: label evidence count changed')
   for e in evidence:
    if full['title'][e['span_start']:e['span_end']]!=e['quote']:
     errors.append(f'{n}: category span cannot be found in original title')
   cites=impact['citation_observations']
   cite_source=cites[0]['source'] if cites else {}
   if slim['citation_query_sha256']!=(cite_source.get('request_fingerprint') or '') or slim['citation_raw_sha256']!=(cite_source.get('raw_sha256') or ''):
    errors.append(f'{n}: citation audit pointer changed')
   refs=json.loads(slim['source_ref_ids_json'])
   if any(not x.startswith('src:') for x in refs):errors.append(f'{n}: malformed source ref')
   if slim['audit_ref']!='master_papers.csv#paper_id='+pid:errors.append(f'{n}: audit ref mismatch')
   for text in slim.values():
    if FORMULA.match(text):errors.append(f'{n}: unsafe spreadsheet formula prefix')
   counts['rows']+=1
   counts['candidate']+=slim['classification_label_status']=='candidate'
   counts['cited']+=bool(slim['citation_count'])
   if len(errors)>12:break
 if counts['rows']!=89530:errors.append(f'row count {counts["rows"]}')
 if digest(args.browse)!=digest(args.gzip,compressed=True):errors.append('gzip does not roundtrip to exact CSV bytes')
 result={'passed':not errors,'rows':counts['rows'],'columns':len(view.fieldnames or []),
         'counts':dict(counts),'master_sha256':digest(args.master),
         'browse_sha256':digest(args.browse),'gzip_sha256':digest(args.gzip),
         'errors':errors[:12]}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)

if __name__=='__main__':main()
