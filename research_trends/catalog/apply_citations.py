#!/usr/bin/env python3
"""Join frozen OpenAlex citation responses to exact, audited master DOI keys."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

def sha(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def canon(value: str):
    s=(value or '').strip().lower()
    for prefix in ('https://doi.org/','http://doi.org/','doi:'):
        if s.startswith(prefix):s=s[len(prefix):]
    return s

def index_responses(directory: Path):
    queries={}
    candidates=defaultdict(list)
    for line in (directory/'query_audit.jsonl').read_text(encoding='utf8').splitlines():
        audit=json.loads(line)
        if audit['http_status']!=200:continue
        raw=directory/'raw'/(audit['query_sha256']+'.json')
        if not raw.is_file() or sha(raw)!=audit['raw_sha256']:
            raise ValueError('missing or changed raw response: '+audit['query_sha256'])
        query=parse_qs(urlsplit(audit['url']).query)['filter'][0]
        requested={canon(x) for x in query.removeprefix('doi:').split('|')}
        data=json.loads(raw.read_text(encoding='utf8'))
        if not isinstance(data.get('results'),list):raise ValueError('missing works array')
        observed=defaultdict(list)
        for work in data['results']:
            doi=canon(work.get('doi'))
            if doi in requested:observed[doi].append(work)
        truncated=(data.get('meta') or {}).get('count',0)>len(data['results'])
        for doi in requested:
            if doi in queries:raise ValueError('DOI requested by two successful batches: '+doi)
            queries[doi]={'audit':audit,'works':observed[doi], 'truncated':truncated}
    return queries

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--master',type=Path,required=True)
    ap.add_argument('--citation-cache',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args()
    output=args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):raise SystemExit('output directory must be empty')
    output.mkdir(parents=True,exist_ok=True)
    queries=index_responses(args.citation_cache)
    counts=Counter()
    dest=output/'master_papers.csv'
    with args.master.open(encoding='utf-8-sig',newline='') as inp,dest.open('w',encoding='utf-8-sig',newline='') as out:
        reader=csv.DictReader(inp)
        fields=reader.fieldnames
        if not fields or 'citation_count' not in fields:raise ValueError('attention columns missing')
        writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
        for row in reader:
            doi=canon(row['doi'])
            if not doi:
                row['citation_status']='no_verified_doi'
            elif doi not in queries:
                row['citation_status']='not_collected'
            else:
                q=queries[doi];works=q['works'];audit=q['audit']
                if not works:
                    row['citation_status']='possibly_truncated' if q['truncated'] else 'not_found_exact_doi'
                elif len(works)>1:
                    row['citation_status']='ambiguous_exact_doi'
                else:
                    work=works[0]
                    value=work.get('cited_by_count')
                    if not isinstance(value,int) or isinstance(value,bool) or value<0:
                        row['citation_status']='provider_count_missing'
                    else:
                        row['citation_count']=str(value)
                        row['citation_provider']='OpenAlex'
                        row['citation_as_of']=audit['at_utc']
                        row['citation_status']='reported_exact_doi'
                        row['provider_work_id']=work.get('id') or ''
                        row['attention_evidence_json']=json.dumps([{'field':'citation_count',
                            'match_basis':'exact_verified_doi','doi':doi,'query_sha256':audit['query_sha256'],
                            'raw_sha256':audit['raw_sha256'],'provider_work_id':row['provider_work_id'],
                            'provider_updated_date':work.get('updated_date') or '',
                            'source_ref':'citation_audit:'+audit['query_sha256']}],ensure_ascii=False,separators=(',',':'))
                        if work.get('is_retracted') is True:row['retraction_status']='openalex_reported_retracted'
                        elif work.get('is_retracted') is False:row['retraction_status']='openalex_reported_not_retracted'
            writer.writerow(row)
            counts[row['citation_status']]+=1
    with dest.open('rb') as source,(output/'master_papers.csv.gz').open('wb') as sink:
        with gzip.GzipFile(filename='',mode='wb',fileobj=sink,compresslevel=9,mtime=0) as archive:
            for chunk in iter(lambda:source.read(1<<20),b''):archive.write(chunk)
    receipt={'rows':sum(counts.values()),'columns':len(fields),'citation_status_counts':dict(counts),
             'matched_queried_dois':len(queries),'source_master_sha256':sha(args.master),
             'citation_audit_sha256':sha(args.citation_cache/'query_audit.jsonl'),
             'csv_bytes':dest.stat().st_size,'csv_sha256':sha(dest),
             'gzip_bytes':(output/'master_papers.csv.gz').stat().st_size,
             'gzip_sha256':sha(output/'master_papers.csv.gz')}
    (output/'citation_join_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
