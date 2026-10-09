from pathlib import Path
import json,csv,collections
P=Path(__file__).parent;S=P/'systems'
rows=[json.loads(x) for x in (P/'papers.jsonl').read_text().splitlines()]
manifest=json.loads((S/'sources_manifest.json').read_text());m={(s['conference'],s['year']):s for s in manifest}
for x in map(json.loads,(S/'systems_research_papers.jsonl').read_text().splitlines()):
 src=m[(x['conference'],x['year'])];hashes=src.get('sha256',{});hashes=hashes if isinstance(hashes,dict) else {'source':hashes}
 r=dict(venue=x['conference'],year=x['year'],track=x['track'],title=x['title'],authors=x.get('authors_text',''),abstract=x.get('abstract') or '',doi=x.get('doi') or '',stable_id=x.get('id'),id_kind='derived_title_hash',official_url=x.get('url') or x['source_url'],source_url=x['source_url'],source_file='systems/sources_manifest.json',source_sha256='',source_hashes=hashes,retrieved_at=x['retrieved_date_utc'],main_research=x['main_research'],classification_text='title',session=x.get('session'),proceedings_toc_url=x.get('proceedings_toc_url'),source_format=x.get('source_format'))
 rows.append(r)
with open(P/'combined_papers.jsonl','w',encoding='utf8') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
cols=['venue','year','track','title','authors','abstract','doi','stable_id','id_kind','official_url','source_url','source_file','source_sha256','retrieved_at','main_research','classification_text']
with open(P/'combined_papers.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
print('combined research',len(rows),collections.Counter(x['venue'] for x in rows))
