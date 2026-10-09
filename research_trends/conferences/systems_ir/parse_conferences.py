"""Rebuild title-first metadata from frozen official sources. Python 3.10+, lxml."""
from pathlib import Path
from lxml import html
import json,re,csv,hashlib,collections,unicodedata
from urllib.parse import urljoin,urlparse,parse_qs,unquote
P=Path(__file__).parent; R=P/'raw'; allrows=[]; audits=[]
logs={x['name']:x for x in map(json.loads,(P/'fetch_log.jsonl').read_text().splitlines()) if 'sha256' in x}
def clean(s):return re.sub(r'\s+',' ',s or '').strip()
def norm(s):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',s).lower())
def tree(n):return html.fromstring((R/(n+'.html')).read_bytes().decode('utf-8',errors='replace'))
def txt(e):return clean(e.text_content()) if e is not None else ''
def doi(s):
 m=re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+',unquote(s or ''));return m.group(0).rstrip('.,;_') if m else ''
def rec(n,venue,year,title,track='Research',authors='',abstract='',official_url='',stable_id='',id_kind='',d='',**extra):
 title=clean(title)
 if not title:return
 src=logs[n]; sid=stable_id or d
 if not sid:sid=f'{venue.lower()}:{year}:title_sha256:'+hashlib.sha256(norm(title).encode()).hexdigest();id_kind='derived_normalized_title_hash'
 row=dict(venue=venue,year=year,track=track,title=title,authors=clean(authors),abstract=clean(abstract),doi=d,stable_id=sid,id_kind=id_kind or 'doi',official_url=official_url or src['url'],source_url=src['url'],source_file='raw/'+n+'.html',source_sha256=src['sha256'],retrieved_at=src['retrieved_at'],main_research=True,classification_text='title',**extra)
 allrows.append(row);return row

def proceedings(n):
 out=[]; t=tree(n); section='';current=None
 for el in t.xpath('//*[@id="DLcontent"]/*'):
  if el.tag=='h2':section=txt(el)
  elif el.tag=='h3':
   a=el.xpath('.//a')[0];u=a.get('href') or '';u=parse_qs(urlparse(u).query).get('q',[u])[0]
   current={'title':txt(a),'section':section,'doi':doi(u),'url':u,'abstract':'','authors':''};out.append(current)
  elif current is not None and 'DLauthors' in (el.get('class') or ''):current['authors']='; '.join(txt(x) for x in el.xpath('.//li'))
  elif current is not None and 'DLabstract' in (el.get('class') or ''):current['abstract']=txt(el)
 return out

# ICSE accepted-table membership, rather than scheduled sessions or artifact track.
for year in range(2020,2027):
 n=f'icse{year}';t=tree(n);details={}
 for a in t.xpath('//a[@data-event-modal]'):
  tr=a.xpath('ancestor::tr[1]');links=tr[0].xpath('.//a[contains(@href,"/details/")]/@href') if tr else []
  if links:details[a.get('data-event-modal')]=links[0]
 for tr in t.xpath('//*[@id="event-overview"]//tr[td]'):
  a=tr.xpath('.//a[@data-event-modal]')[0];eid=a.get('data-event-modal');track=''.join(tr.xpath('.//div[@class="prog-track"]/text()'));pubs=tr.xpath('.//a[contains(@class,"publication-link")]/@href');d=next((doi(u) for u in pubs if doi(u)),'')
  rec(n,'ICSE',year,a.text or txt(a),track,'; '.join(txt(x) for x in tr.xpath('.//div[@class="performers"]/a')),official_url=details.get(eid,''),stable_id='researchr:event:'+eid,id_kind='researchr_event_uuid',d=d,publication_urls=pubs)

# SIGIR full/long only; excludes short, perspective, resources and reproducibility.
n='sigir2020';section=''
for el in tree(n).xpath('//h3|//h4'):
 if el.tag=='h3':section=txt(el)
 elif section=='Full Papers' and el.get('class')=='accepted-papers-title':rec(n,'SIGIR',2020,txt(el),'Full Papers',txt(el.getnext()))
for year in [2021,2022]:
 n=f'sigir{year}';section=''
 for el in tree(n).xpath('//h3|//h4|//p'):
  if el.tag in ['h3','h4']:section=txt(el)
  elif section in ['Long Papers','Full Papers']:
   b=el.xpath('./strong|./b')
   if b:rec(n,'SIGIR',year,txt(b[0]),section,clean(''.join(el.itertext()).replace(txt(b[0]),'',1)))
n='sigir2023'
for el in tree(n).xpath('//p[strong]'):
 b=el.xpath('./strong')[0];title=txt(b)
 if title.startswith('●'):rec(n,'SIGIR',2023,title.lstrip('● '),'Full Papers',clean(''.join(el.itertext()).replace(txt(b),'',1)))
n='sigir2024_data'
for x in map(json.loads,(R/(n+'.html')).read_text().splitlines()):
 if x['submssion_id'].startswith('fp'):rec(n,'SIGIR',2024,x['title'],'Full Papers','; '.join(a['name'] for a in x['authors']),stable_id='sigir2024:'+x['submssion_id'],id_kind='official_submission_id')
n='sigir2025_accepted';section='';procs={norm(x['title']):x for x in proceedings('sigir2025')}
for el in tree(n).xpath('//h2|//li[contains(@class,"accepted-paper-item")]'):
 if el.tag=='h2':section=el.get('id')
 elif section=='full-papers':
  title=txt(el.xpath('.//span[@class="accepted-paper-title"]')[0]);a=txt(el.xpath('.//span[@class="accepted-paper-author"]')[0]);pr=procs.get(norm(title),{})
  row=rec(n,'SIGIR',2025,title,'Full Papers',a,pr.get('abstract',''),pr.get('url',''),d=pr.get('doi',''))
  if pr:row['enrichment_source']='https://sigir2025.dei.unipd.it/proceedings.html'

# SIGIR2026 official public page data; acceptance snapshot, not final corrected proceedings.
n='sigir2026_events'
event=json.loads((R/(n+'.html')).read_text())
page=next(x for x in event[0]['localizations'][0]['page_content'] if x['slug']=='/program/accepted-papers')
for b in page['page_name_component']:
 t=html.fromstring(b.get('text_block') or '<div/>')
 for p in t.xpath('//p'):
  if txt(p).startswith('[fp]') and p.xpath('./i'):
   i=p.xpath('./i')[0];title=txt(i);authors=clean(txt(p).replace('[fp]','',1).replace(title,'',1))
   rec(n,'SIGIR',2026,title,'Full Papers',authors,official_url='https://sigir2026.org/en-AU/pages/program/accepted-papers',source_status='official preliminary accepted snapshot; titles not camera-ready corrected')

# KDD official accepted research list / proceedings track boundaries.
n='kdd2020';t=tree(n);section=''
for el in t.xpath('//h2|//li[contains(@class,"media")]'):
 if el.tag=='h2':section=el.get('id')
 elif section=='research-track-papers':
  a=el.xpath('.//a')[0];u=urljoin(logs[n]['url'],a.get('href'));authors=txt(el).split('Authors:',1)[-1];rec(n,'KDD',2020,txt(a),'Research Track',authors,official_url=u,stable_id=u,id_kind='official_paper_url')
for year in [2021,2022,2023]:
 n=f'kdd{year}'
 for x in proceedings(n):
  if 'Research Track' in x['section']:rec(n,'KDD',year,x['title'],x['section'].replace('SESSION: ',''),x['authors'],x['abstract'],x['url'],d=x['doi'])
for year in [2024,2025]:
 n='kdd2024' if year==2024 else 'kdd2025_papers';t=tree(n)
 for tr in t.xpath('//table//tr[td/strong]'):
  title=' '.join(txt(x) for x in tr.xpath('./td/strong'));a=txt(tr.getnext());d=doi(txt(tr));rec(n,'KDD',year,title,'Research Track',a,official_url=('https://doi.org/'+d if d else ''),d=d)
n='kdd2026_papers';s=(R/(n+'.html')).read_text()
for m in re.finditer(r'const (cycle\dPapers) = ',s):
 ary=json.JSONDecoder().raw_decode(s[m.end():])[0]
 for x in ary:
  if x['track']=='rtp':rec(n,'KDD',2026,x['title'],'Research Track',x['authors'],official_url=x['url'],d=doi(x['url']),cycle=m.group(1))

# Enrich exact title matches from official SIGIR proceedings without changing cohort.
for year in [2022,2024]:
 n=f'sigir{year}_proceedings'
 if (R/(n+'.html')).exists():
  bytitle={norm(x['title']):x for x in proceedings(n)}
  for row in allrows:
   if row['venue']=='SIGIR' and row['year']==year:
    pr=bytitle.get(norm(row['title']))
    if pr:
     row.update(abstract=pr['abstract'],doi=pr['doi'],official_url='https://doi.org/'+pr['doi'],enrichment_source=logs[n]['url'],enrichment_source_sha256=logs[n]['sha256'])

# Deduplicate within venue/year by DOI, official UUID, then normalized title.
seen=set();rows=[]
for r in allrows:
 k=(r['venue'],r['year'],norm(r['title']))
 if k in seen:audits.append({'deduplicated':k,'stable_id':r['stable_id']});continue
 seen.add(k);rows.append(r)
with open(P/'papers.jsonl','w',encoding='utf8') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
cols=['venue','year','track','title','authors','abstract','doi','stable_id','id_kind','official_url','source_url','source_file','source_sha256','retrieved_at','main_research','classification_text']
with open(P/'papers.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
counts=[]
for (v,y),a in __import__('itertools').groupby(sorted(rows,key=lambda r:(r['venue'],r['year'])),lambda r:(r['venue'],r['year'])):
 a=list(a);counts.append({'venue':v,'year':y,'n_main':len(a),'with_abstract':sum(bool(x['abstract']) for x in a),'with_doi':sum(bool(x['doi']) for x in a)})
(P/'coverage.json').write_text(json.dumps(counts,indent=2));(P/'parse_audit.json').write_text(json.dumps(audits,indent=2));print(json.dumps(counts,indent=2));print('TOTAL',len(rows),'deduplicated',len(audits))
