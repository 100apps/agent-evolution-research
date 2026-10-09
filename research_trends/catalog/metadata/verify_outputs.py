#!/usr/bin/env python3
"""Validate a delivered metadata patch and its provenance, without network access."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);args=ap.parse_args();p=args.directory
 cov=json.loads((p/'coverage.json').read_text(encoding='utf-8'));manifest=json.loads((p/'source_manifest.json').read_text(encoding='utf-8'))
 sources={s['source_path']:s['source_sha256'] for s in manifest['sources']};source_ids={s.get('source_id'):s for s in manifest['sources'] if s.get('source_id')};seen=set();rows=0;counts=collections.Counter();venues=collections.Counter();entities=set();errors=[]
 with gzip.open(p/'metadata_patch.jsonl.gz','rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line);rows+=1;pid=r['occurrence_id'];venues[r['venue']]+=1;entities.add(r['paper_entity_id'])
   if pid in seen:errors.append((pid,'duplicate occurrence'))
   seen.add(pid)
   for field in ('authors','institutions','countries','doi','arxiv_id','openreview_id','publication_date'):
    if r.get(field):counts[field]+=1
    meta=r['field_provenance'][field]
    if r.get(field) and meta['status']=='missing':errors.append((pid,field+' has value but status missing'))
    if r.get(field) and meta['missing_reason']:errors.append((pid,field+' has value but missing reason nonempty'))
   for field,meta in r['field_provenance'].items():
    for ev in meta['evidence']:
     if ev.get('source_ref'):
      if ev['source_ref'] not in source_ids:errors.append((pid,field+' source reference missing from manifest'))
     elif sources.get(ev['source_path'])!=ev['source_sha256']:errors.append((pid,field+' evidence differs from manifest'))
   for a in r['authors']:
    if not a['name'].strip() and a.get('name_status')!='missing_source_name':errors.append((pid,'unmarked empty author name'))
    for aff in a['affiliations']:
     if aff['temporal_status']=='publication_time_unverified' and aff.get('country_code'):errors.append((pid,'country inferred from time-unverified profile'))
   for k,v in r['dedup_identifiers'].items():
    if k not in ('doi','arxiv_id','openreview_id'):errors.append((pid,'unsupported dedup ID'))
    elif str(r[k]).lower()!=str(v).lower():errors.append((pid,'dedup ID differs from field'))
 if rows!=cov['total']['source_occurrences']:errors.append(('total','count mismatch'))
 for field,count in counts.items():
  if count!=cov['total'][field]['present']:errors.append((field,'coverage count mismatch'))
 for venue,count in venues.items():
  if count!=cov['by_venue'][venue]['source_occurrences']:errors.append((venue,'count mismatch'))
 if len(entities)!=cov['unique_exact_id_entities']:errors.append(('entities','count mismatch'))
 report={'passed':not errors,'source_occurrences':rows,'exact_id_entities':len(entities),'sources':len(sources),'field_counts':dict(counts),'venue_counts':dict(venues),'errors':errors[:50]}
 print(json.dumps(report,ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
