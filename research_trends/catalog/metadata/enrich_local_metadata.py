#!/usr/bin/env python3
"""Offline, stdlib-only enrichment of frozen conference/original39 metadata.
No network access. Never joins papers by title. See README_zh.md for semantics.
Python 3.9+. Paths are relative to --conferences-root and --original39-root.
"""
import argparse, calendar, collections, csv, datetime, gzip, hashlib, html, io, json, re
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, parse_qs, unquote
import xml.etree.ElementTree as ET
VERSION='1.0.0'
FIELDS=('authors','institutions','countries','doi','arxiv_id','openreview_id','publication_date','abstract')
MONTHS={m.lower():i for i,m in enumerate(calendar.month_name) if m}
COUNTRIES={'USA':('US','United States'),'US':('US','United States'),'U.S.A.':('US','United States'),'United States':('US','United States'),'United States of America':('US','United States'),'UK':('GB','United Kingdom'),'United Kingdom':('GB','United Kingdom'),'China':('CN','China'),'P. R. China':('CN','China'),'P.R. China':('CN','China'),'PR China':('CN','China'),'Australia':('AU','Australia'),'Canada':('CA','Canada'),'Germany':('DE','Germany'),'France':('FR','France'),'Japan':('JP','Japan'),'Singapore':('SG','Singapore'),'India':('IN','India'),'Italy':('IT','Italy'),'Spain':('ES','Spain'),'Switzerland':('CH','Switzerland'),'Netherlands':('NL','Netherlands'),'Sweden':('SE','Sweden'),'Norway':('NO','Norway'),'Finland':('FI','Finland'),'Denmark':('DK','Denmark'),'Austria':('AT','Austria'),'Ireland':('IE','Ireland'),'Israel':('IL','Israel'),'South Korea':('KR','South Korea'),'Republic of Korea':('KR','South Korea'),'New Zealand':('NZ','New Zealand'),'Brazil':('BR','Brazil'),'Portugal':('PT','Portugal'),'Poland':('PL','Poland'),'Belgium':('BE','Belgium'),'Czech Republic':('CZ','Czech Republic'),'Taiwan':('TW','Taiwan'),'Hong Kong':('HK','Hong Kong')}
# Country/region tokens are recognized only as a COMPLETE comma-delimited location
# component in paper-scoped affiliation text, never as institution-name substrings.
def clean(s):return re.sub(r'\s+',' ',html.unescape(str(s or ''))).strip()
def txt(e):return clean(''.join(e.itertext())) if e is not None else ''
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jread(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jlread(p):
 with p.open(encoding='utf-8-sig') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def unique(xs):return list(dict.fromkeys(xs))
def canon_url(s):
 u=urlparse(html.unescape(s or ''));return (u.hostname or '').lower()+unquote(u.path).rstrip('/')+('?' + u.query if u.query else '')
def ids_from_urls(urls):
 out={}
 for s in urls:
  if not s:continue
  u=urlparse(str(s));h=(u.hostname or '').lower();path=unquote(u.path)
  if h in ('openreview.net','www.openreview.net') and u.path in ('/forum','/pdf'):
   value=parse_qs(u.query).get('id',[''])[0]
   if re.fullmatch(r'[A-Za-z0-9_-]+',value):out['openreview_id']=value
  if h in ('arxiv.org','www.arxiv.org','export.arxiv.org'):
   m=re.match(r'^/(?:abs|pdf|html)/(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?(?:\.pdf)?/?$',path)
   if m:out['arxiv_id']=m.group(1)
  if h in ('doi.org','dx.doi.org','dl.acm.org'):
   s=path.lstrip('/')
   if h=='dl.acm.org':s=re.sub(r'^doi/(?:abs/|full/|pdf/)?','',s)
   if re.fullmatch(r'10\.\d{4,9}/\S+',s):out['doi']=s.lower()
 return out
class AttrParser(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.anchors=[];self.inputs=[]
 def handle_starttag(self,t,a):
  d=dict(a)
  if t=='a' and d.get('href'):self.anchors.append(d['href'])
  if t=='input':self.inputs.append(d)
def attrs(s):p=AttrParser();p.feed(s);return p
class Plain(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.parts=[]
 def handle_data(self,d):self.parts.append(d)
def plain(s):p=Plain();p.feed(s);return clean(' '.join(p.parts))
def author(name,affiliations=None,**extra):
 a=dict(name=clean(name),affiliations=affiliations or [],**extra)
 if not a['name']:a.update(name_status='missing_source_name',name_missing_reason='empty_name_in_source')
 return a

def source_id(path,digest):return 'src:'+hashlib.sha256((path+'\0'+digest).encode()).hexdigest()[:20]
def compact_provenance(provenance):
 result={}
 for field,meta in provenance.items():
  result[field]={k:v for k,v in meta.items() if k!='evidence'}
  result[field]['evidence']=[{'source_ref':source_id(e['source_path'],e['source_sha256']),**{k:v for k,v in e.items() if k not in ('source_path','source_sha256','source_url')}} for e in meta['evidence']]
 return result
def affiliation(name,temporal='paper_scoped_explicit'):
 a={'name':clean(name),'temporal_status':temporal,'country_code':'','country_name':'','country_status':'missing','country_missing_reason':'no_explicit_affiliation_country'}
 if temporal=='paper_scoped_explicit':
  parts=[clean(x).rstrip('.') for x in a['name'].split(',')]
  # Exact standalone country text is permitted; names containing country words are not.
  candidates=[COUNTRIES[p] for p in parts[1:] if p in COUNTRIES]
  if len(set(candidates))==1:
   a.update(country_code=candidates[0][0],country_name=candidates[0][1],country_status='explicit_location_token',country_missing_reason='')
 elif temporal=='publication_time_unverified':a['country_missing_reason']='institution_profile_is_not_historical_location_evidence'
 return a
class Sources:
 def __init__(self,roots):self.roots=roots;self.entries={};self.metadata={};self.failures=[]
 def add(self,p,url='',locator='',method='raw_exact_identifier',scope='conferences'):
  p=Path(p);root=self.roots[scope]
  key=scope+'/'+p.relative_to(root).as_posix()
  if key not in self.entries:
   if not p.is_file():self.failures.append({'source_path':key,'reason':'file_missing'});return {'source_path':key,'source_sha256':'','source_available':False,'locator':locator,'method':method}
   m=self.metadata.get(str(p),{})
   self.entries[key]={'source_path':key,'source_sha256':sha(p),'bytes':p.stat().st_size,'source_url':url or m.get('url',''),'retrieved_at':m.get('retrieved_at','')}
  e=self.entries[key];e['source_id']=source_id(key,e['source_sha256'])
  return {'source_path':key,'source_sha256':e['source_sha256'],'source_url':url or e.get('source_url',''),'locator':locator,'method':method}
 def manifests(self,b):
  for p in b.glob('*/*manifest.json'):
   try:
    data=jread(p)
    if not isinstance(data,list):continue
    for r in data:
     if isinstance(r,dict) and isinstance(r.get('file'),str):
      q=p.parent/r['file'];q=q if q.exists() else p.parent/'raw'/r['file']
      self.metadata[str(q)]={'url':r.get('url') or r.get('source_url',''),'retrieved_at':r.get('retrieved_at') or r.get('fetched_at','')}
   except (ValueError,TypeError):pass
  for p in b.glob('nlp_vision/raw/*.manifest.json'):
   m=jread(p);q=Path(str(p)[:-14]);self.metadata[str(q)]={'url':m.get('source_url',''),'retrieved_at':m.get('fetched_at','')}
class RawIndex:
 def __init__(self,b,sources):self.b=b;self.s=sources;self.data={};self.events=collections.defaultdict(list);self.icml_or={};self.nips_auth={};self.warnings=[]
 def put(self,key,item):
  if key in self.data and self.data[key]!=item:self.warnings.append({'key':key,'reason':'multiple_raw_candidates_first_preserved'});return
  self.data[key]=item
 def build(self):
  b=self.b
  for p in sorted((b/'nlp_vision/raw').glob('acl_*.xml')):
   root=ET.parse(p).getroot()
   for v in root.findall('volume'):
    for r in v.findall('paper'):
     pid=root.get('id')+'-'+v.get('id')+'.'+r.get('id');au=[]
     for a in r.findall('author'):
      aa=author(' '.join(filter(None,[txt(a.find('first')),txt(a.find('last'))])),[affiliation(txt(f)) for f in a.findall('affiliation') if txt(f)],**{'author_id':a.get('id',''),'orcid':a.get('orcid','')})
      au.append(aa)
     month=MONTHS.get(txt(v.find('meta/month')).lower());year=txt(v.find('meta/year'));date=f'{year}-{month:02d}' if month else year
     self.put(('ACL',pid),{'authors':au,'publication_date':date,'date_precision':'month' if month else 'year','date_type':'proceedings_bibliographic_date','doi':txt(r.find('doi')),'abstract':txt(r.find('abstract')),'evidence':self.s.add(p,locator='paper:'+pid),'author_status':'source_ordered'})
  for p in sorted((b/'nlp_vision/raw').glob('cvpr*.html')):
   if p.name not in {'cvpr_2020_day16.html','cvpr_2020_day17.html','cvpr_2020_day18.html'} and not re.fullmatch(r'cvpr_202[1-6]\.html',p.name):continue
   text=p.read_text(encoding='utf-8')
   chunks=re.split(r'(?=<dt\s+class=[\"\x27]ptitle[\"\x27])',text)
   for block in chunks[1:]:
    a=attrs(block);url=next((urljoin('https://openaccess.thecvf.com',u) for u in a.anchors if '/html/' in u and '_paper.html' in u),'')
    if not url:continue
    authors=[author(x['value']) for x in a.inputs if x.get('name') in ('query_author','query') and x.get('value')]
    month=re.search(r'\bmonth\s*=\s*\{([^}]+)\}',block);year=re.search(r'\byear\s*=\s*\{(\d{4})\}',block)
    mo=MONTHS.get(clean(month[1]).lower()) if month else None;date=(year[1]+(f'-{mo:02d}' if mo else '')) if year else ''
    self.put(('CVPR',canon_url(url)),{'authors':authors,'publication_date':date,'date_precision':'month' if mo else 'year','date_type':'proceedings_bibliographic_date','links':a.anchors,'evidence':self.s.add(p,locator='paper_url:'+url),'author_status':'source_ordered'})
  # The published local snapshots use shorter filenames than the transfer
  # environment. Select only saved conference program JSON, never manifests.
  program_files=list((b/'ml/raw').glob('iclr_20??.json'))+list((b/'ml/raw').glob('icml_20??_program.json'))+list((b/'ml/raw').glob('neurips_20??_program.json'))
  for p in sorted(program_files):
   m=re.match(r'(iclr|icml|neurips)_(\d{4})(?:_program)?\.json$',p.name)
   if not m:continue
   v,y=m[1],int(m[2]);
   if v=='iclr' and y==2020:continue  # legacy OpenReview list handled by forum ID below
   data=jread(p)
   for i,e in enumerate(data.get('results',[])):
    if e.get('eventtype')!='Poster':continue
    urls=[e.get('paper_url'),e.get('paper_pdf_url')]+[q.get('uri') for q in e.get('eventmedia',[])]
    ids=ids_from_urls(urls);au=[author(a.get('fullname',''),[affiliation(a['institution'],'publication_time_unverified')] if a.get('institution') else []) for a in e.get('authors',[])]
    item={'authors':au,'event':e['id'],'program_date':e.get('starttime',''),'ids':ids,'abstract':e.get('abstract') or '', 'evidence':self.s.add(p,locator=f'results[{i}];event_id={e["id"]}'),'author_status':'source_ordered_profile_institution_time_unverified'}
    if ids.get('openreview_id'):self.events[(v,y,'openreview',ids['openreview_id'])].append(item)
    if e.get('uid'):self.events[(v,y,'uid',e['uid'])].append(item)
  for p in sorted((b/'ml/raw').glob('icml_20??.html')):
   y=int(p.stem.split('_')[1]);text=p.read_text(encoding='utf-8')
   for block in re.split(r'<div\s+class=[\"\x27]paper[\"\x27]\s*>',text)[1:]:
    aa=attrs(block).anchors;url=next((u for u in aa if 'proceedings.mlr.press/' in u and u.endswith('.html')),'');ids=ids_from_urls(aa)
    if url and ids.get('openreview_id'):self.icml_or[canon_url(url)]=(ids['openreview_id'],self.s.add(p,locator='paper_url:'+url))
  for p in sorted((b/'ml/raw').glob('icml_*_citeproc.yaml')):
   # Constrained extraction of scalar URL/published fields only. Not a general YAML parser.
   for block in re.split(r'(?m)^- title:',p.read_text(encoding='utf-8'))[1:]:
    u=re.search(r'^  URL: (\S+)\s*$',block,re.M);d=re.search(r'^  published: [\"\x27]?(\d{4}-\d{2}-\d{2})',block,re.M)
    if u and d:self.put(('PMLR_DATE',canon_url(u[1])),{'publication_date':d[1],'date_precision':'day','date_type':'proceedings_published_field','evidence':self.s.add(p,locator='URL:'+u[1])})
  for p in sorted((b/'ml/raw').glob('neurips_20??.html')):
   y=int(p.stem.split('_')[1]);text=p.read_text(encoding='utf-8')
   for block in re.findall(r'<li\b[^>]*>.*?</li>',text,re.S):
    a=attrs(block).anchors;u=next((x for x in a if '/hash/' in x and 'Abstract' in x),'');m=re.search(r'/hash/([^-]+)-',u);au=re.search(r'<span\s+class=[\"\x27]paper-authors[\"\x27][^>]*>(.*?)</span>',block,re.S)
    if m and au:self.nips_auth[(y,m[1])]=([author(x) for x in plain(au[1]).split(',') if clean(x)],self.s.add(p,locator='paper_hash:'+m[1]))
  for p in sorted((b/'systems_ir/raw').glob('icse*.html')):
   text=p.read_text(encoding='utf-8')
   for block in re.findall(r'<tr\b[^>]*>.*?</tr>',text,re.S):
    eid=re.search(r'data-event-modal=[\"\x27]([^\"\x27]+)',block);perform=re.search(r'<div\s+class=[\"\x27]performers[\"\x27][^>]*>(.*?)</div>',block,re.S)
    if not eid or not perform:continue
    au=[]
    pattern=r'<a\b[^>]*>(.*?)</a>\s*(?:<span\s+class=[\"\x27]prog-aff[\"\x27][^>]*>(.*?)</span>)?'
    for a,f in re.findall(pattern,perform[1],re.S):au.append(author(plain(a),[affiliation(plain(f),'publication_time_unverified')] if clean(f) else []))
    key=('ICSE','researchr:event:'+eid[1]);item={'authors':au,'evidence':self.s.add(p,locator='data-event-modal:'+eid[1]),'author_status':'source_ordered_program_profile_time_unverified'}
    if key not in self.data or len(au)>len(self.data[key]['authors']):self.data[key]=item
  p=b/'systems_ir/raw/sigir2024_data.html'
  if p.exists():
   for i,r in enumerate(jlread(p),1):
    self.put(('SIGIR','sigir2024:'+r['submssion_id']),{'authors':[author(a['name'],[affiliation(a['affiliation'])] if a.get('affiliation') else []) for a in r['authors']],'evidence':self.s.add(p,locator='line:'+str(i)+';submission:'+r['submssion_id']),'author_status':'source_ordered'})
 def event(self,key):
  xs=self.events.get(key,[])
  if not xs:return None
  # No union of conflicting lists. Preserve one complete source and flag conflicts.
  first=max(xs,key=lambda x:sum(bool(a['affiliations']) for a in x['authors']))
  if len({json.dumps(x['authors'],sort_keys=True,ensure_ascii=False) for x in xs})>1:first={**first,'event_author_conflict':True}
  return first

def split_top(s,delimiters=',;',split_and=False):
 out=[];cur=[];depth=0;i=0
 while i<len(s):
  c=s[i]
  if c=='(':depth+=1
  elif c==')':depth=max(0,depth-1)
  word=split_and and depth==0 and s[i:i+5]==' and '
  if depth==0 and (c in delimiters or word):
   out.append(clean(''.join(cur)));cur=[];i+=5 if word else 1
  else:cur.append(c);i+=1
 out.append(clean(''.join(cur)));return [x for x in out if x]
def parse_system_authors(r):
 s=r.get('authors','');v=r['venue'];au=[]
 if not s:return [],'missing','source_has_no_author_text'
 if v=='OSDI':return [],'unparsed','author_affiliation_comma_boundary_ambiguous'
 if ';' in s:parts=split_top(s,';',v=='SOSP')
 else:parts=split_top(s,',',v=='SOSP')
 for part in parts:
  part=re.sub(r'^and\s+','',part).strip()
  if v=='SOSP' and ')' in part:
   # Parenthesis nesting is retained. No backward propagation to preceding names.
   m=re.fullmatch(r'(.+?)\s*\((.*)\)',part)
   if m:au.append(author(m[1],[affiliation(m[2])]))
   else:return [],'unparsed','parenthetical_affiliation_boundary_ambiguous'
  elif '(' in part:
   m=re.fullmatch(r'(.+?)\s*\((.*)\)',part)
   if not m:return [],'unparsed','parenthetical_affiliation_boundary_ambiguous'
   au.append(author(m[1],[affiliation(m[2])]))
  elif ':' in part and (v,r['year']) in [('SIGIR',2020),('KDD',2020)]:
   name,aff=part.split(':',1);au.append(author(name,[affiliation(aff)] if clean(aff) else []))
  else:
   for name in re.split(r'\s+and\s+',part):
    if clean(name):au.append(author(name))
 return au,'parsed_explicit_delimiters',''

def evidence_field(value,evidence,status=None,missing='not_in_available_source',**more):
 return dict(status=status or ('present' if value else 'missing'),missing_reason='' if value else missing,evidence=evidence,**more)
def apply_auth(out,au,ev,status='source_ordered',missing='not_in_available_source'):
 if any(not a.get('name') for a in au):status+=':partial_names'
 out['authors']=au;out['field_provenance']['authors']=evidence_field(au,ev,status if au else 'missing',missing)
 affs=[f for a in au for f in a.get('affiliations',[]) if f.get('name')]
 out['institutions']=unique(f['name'] for f in affs)
 out['field_provenance']['institutions']=evidence_field(out['institutions'],ev,'present_publication_time_unverified' if affs and all(f['temporal_status']=='publication_time_unverified' for f in affs) else None,missing='no_affiliation_in_identity_verified_linked_source')
 out['countries']=unique(f['country_code'] for f in affs if f.get('country_code'))
 out['field_provenance']['countries']=evidence_field(out['countries'],ev,missing='no_explicit_publication_time_affiliation_country')
 out['author_affiliation_completeness']='missing' if not affs else 'complete' if all(a.get('affiliations') for a in au) else 'partial'
 out['affiliation_author_count']=sum(bool(a.get('affiliations')) for a in au)
 out['publication_time_affiliation_author_count']=sum(any(f['temporal_status']=='paper_scoped_explicit' for f in a.get('affiliations',[])) for a in au)
 out['country_author_count']=sum(any(f.get('country_code') for f in a.get('affiliations',[])) for a in au)

def enrich(r,p,line,group,idx,s):
 pid=r.get('paper_id') or r.get('stable_id');v=r['venue'];year=r['year']
 ev=s.add(p,locator='line:'+str(line),method='normalized_record');f={}
 out={'source_group':group,'source_paper_id':pid,'occurrence_id':v+':'+str(year)+':'+hashlib.sha256((r.get('track','')+'\0'+pid).encode()).hexdigest()[:20],'venue':v,'year':year,'track':r.get('track',''),'title':r['title'],'official_url':r.get('official_url',''),'program_url':r.get('program_url',''),'authors_raw':r.get('authors',[]),'authors':[],'institutions':[],'countries':[],'doi':r.get('doi',''),'arxiv_id':'','openreview_id':r.get('openreview_id',''),'publication_date':'','date_precision':'','date_type':'','program_date':'','abstract':r.get('abstract') or '','field_provenance':f,'dedup_identifiers':{},'warnings':[]}
 for field in FIELDS:f[field]=evidence_field(out.get(field),[ev],missing='not_in_normalized_record')
 for field in ('doi','openreview_id'):
  if out[field]:f[field]['status']='reported_identifier_not_yet_raw_verified'
 urls=[r.get('official_url','')]+r.get('publication_urls',[]);ids=ids_from_urls(urls)
 for field,value in ids.items():
  if not out.get(field):out[field]=value;f[field]=evidence_field(value,[ev],status='reported_identifier_not_yet_raw_verified')
 # Exact raw-record identity validation, never title matching.
 raw=idx.data.get((v,canon_url(out['official_url']) if v=='CVPR' else pid))
 if raw:
  apply_auth(out,raw['authors'],[raw['evidence']],raw['author_status'])
  if v=='ACL':
   out['doi']=raw['doi'];f['doi']=evidence_field(out['doi'],[raw['evidence']]);
   if out['doi']:out['dedup_identifiers']['doi']=out['doi'].lower()
  if raw.get('publication_date'):
   for k in ('publication_date','date_precision','date_type'):out[k]=raw[k]
   f['publication_date']=evidence_field(out['publication_date'],[raw['evidence']],status='present_'+out['date_precision']+'_precision')
  if raw.get('links'):
   for field,value in ids_from_urls([urljoin('https://openaccess.thecvf.com',u) for u in raw['links']]).items():out[field]=value;f[field]=evidence_field(value,[raw['evidence']]);out['dedup_identifiers'][field]=value
 elif group=='systems_ir':
  au,status,reason=parse_system_authors(r);apply_auth(out,au,[ev],status,reason)
 elif isinstance(r.get('authors'),list):apply_auth(out,[author(a) for a in r['authors']],[ev],'normalized_ordered')
 if group=='ml':
  event=None;orid='';link_ev=[]
  if v=='ICLR' or (v=='NeurIPS' and year==2026):
   orid=ids.get('openreview_id') or (pid.split(':',1)[1] if pid.startswith('openreview:') else '')
   event=idx.event((v.lower(),year,'openreview',orid))
   # ICLR2020 raw forum IDs are verified separately from the archived catalog.
   if v=='ICLR' and year==2020:
    rawfile=idx.b/'ml/raw/iclr_2020.json'
    if not hasattr(idx,'iclr20'):idx.iclr20={x['forum']:x for x in jread(rawfile)} if rawfile.exists() else {}
    d=idx.iclr20.get(orid)
    if d:
     ee=s.add(rawfile,locator='forum:'+orid);apply_auth(out,[author(a) for a in d['content'].get('authors',[])],[ee]);out['dedup_identifiers']['openreview_id']=orid;f['openreview_id']=evidence_field(orid,[ee]);out['openreview_id']=orid
  elif v=='ICML':
   cross=idx.icml_or.get(canon_url(out['official_url']))
   if cross:orid=cross[0];link_ev=[cross[1]];event=idx.event(('icml',year,'openreview',orid));out['dedup_identifiers']['openreview_id']=orid;out['openreview_id']=orid;f['openreview_id']=evidence_field(orid,link_ev)
   d=idx.data.get(('PMLR_DATE',canon_url(out['official_url'])))
   if d:
    for k in ('publication_date','date_precision','date_type'):out[k]=d[k]
    f['publication_date']=evidence_field(out['publication_date'],[d['evidence']],'present_day_precision')
  elif v=='NeurIPS':
   ph=pid.rsplit(':',1)[-1];event=idx.event(('neurips',year,'uid',ph))
   if not event:
    authors=idx.nips_auth.get((year,ph))
    if authors:apply_auth(out,authors[0],[authors[1]],'source_delimited_ordered')
  if event:
   apply_auth(out,event['authors'],link_ev+[event['evidence']],event['author_status']);out['program_date']=event['program_date'];f['program_date']=evidence_field(out['program_date'],link_ev+[event['evidence']],missing='program_datetime_not_in_source')
   for field,value in event['ids'].items():out[field]=value;out['dedup_identifiers'][field]=value;f[field]=evidence_field(value,link_ev+[event['evidence']])
   if event.get('event_author_conflict'):out['warnings'].append('duplicate_raw_program_events_have_conflicting_author_metadata_one_source_preserved')
  elif out.get('openreview_id') and not out['dedup_identifiers'].get('openreview_id'):out['warnings'].append('inherited_openreview_link_may_come_from_upstream_title_join_not_dedup_eligible')
  if v=='NeurIPS' and year<2026 and not event and out['abstract']:f['abstract']['status']='inherited_upstream_title_join_possible'
 if group=='systems_ir' and out['doi']:
  # DOI-primary proceedings entries or DOI linked directly in the accepted event.
  direct=(v=='KDD' and year in (2021,2022,2023,2024,2025,2026)) or (v=='ICSE' and bool(r.get('publication_urls')))
  if direct:out['dedup_identifiers']['doi']=out['doi'].lower();f['doi']['status']='source_native_identifier'
  else:out['warnings'].append('inherited_doi_from_accepted_to_proceedings_title_crosswalk_not_dedup_eligible')
 if not out['authors']:out['warnings'].append('structured_authors_missing_see_authors_raw')
 return out

def original_rows(root,supp,s):
 p=root/'agent_evolution_map.json';data=jread(p);manual={str(r['inventory_index']):r for r in (jread(supp).get('records',[]) if supp and supp.exists() else [])}
 for g in data['groups']:
  for r in g['papers']:
   pid=str(r['inventory_index']);ids=ids_from_urls(r['source_urls']);ev=s.add(p,scope='original39',locator='inventory_index:'+pid,method='curated_source_identity')
   o={'source_group':'original39','source_paper_id':pid,'occurrence_id':'original39:'+pid,'venue':'Original39','year':None,'track':g['id'],'title':r['primary_title'],'official_url':r['source_urls'][0],'source_urls':r['source_urls'],'authors_raw':'','authors':[],'institutions':[],'countries':[],'doi':ids.get('doi',''),'arxiv_id':ids.get('arxiv_id',''),'openreview_id':ids.get('openreview_id',''),'publication_date':'','version_date':'','date_precision':'','date_type':'','program_date':'','abstract':'','field_provenance':{},'dedup_identifiers':{},'warnings':['source_curated_research_collection_not_conference_census']}
   for field in FIELDS:o['field_provenance'][field]=evidence_field(o.get(field),[ev],status='curated_source_link_unverified' if o.get(field) else None)
   apply_auth(o,[],[ev],missing='local_primary_text_not_structurally_extracted')
   m=manual.get(pid)
   if m and m.get('source_path') and m.get('eligible_for_identity_verified_merge',True):
    match=any(ids.get(k) and ids[k]==m.get('identity',{}).get(k) for k in ('doi','arxiv_id','openreview_id')) or bool(m.get('primary_source_url') and canon_url(m['primary_source_url']) in [canon_url(u) for u in r['source_urls']])
    if not match:o['warnings'].append('supplement_identity_mismatch_not_applied')
    else:
     scope=m.get('source_root','original39');src=s.roots[scope]/m['source_path']
     if not src.exists() or sha(src)!=m['source_sha256']:o['warnings'].append('supplement_source_hash_mismatch_not_applied')
     else:
      ee=s.add(src,url=m.get('primary_source_url',''),scope=scope,locator=m['locator'],method=m.get('identity_status','manual_primary_page_verified_identifier'));au=[]
      evs=[ee];bridge_failure=False
      for bridge in m.get('bridge_evidence',[]):
       bscope=bridge.get('source_root','original39');bp=s.roots[bscope]/bridge['source_path']
       if not bp.is_file() or sha(bp)!=bridge['source_sha256']:bridge_failure=True;continue
       be=s.add(bp,scope=bscope,locator=bridge.get('locator',''),method=bridge.get('strength','supporting_identity_bridge'));be['relationship']=bridge.get('relationship','');evs.append(be)
      if bridge_failure:
       o['warnings'].append('supplement_bridge_source_hash_mismatch_not_applied');yield o;continue
      o['supplement_identity_status']=m.get('identity_status','')
      o['supplement_affiliation_bridge_status']=m.get('affiliation_bridge_status','')
      for a in m.get('authors',[]):
       affs=[]
       for f in a.get('affiliations',[]):
        item=affiliation(f['name']);
        if f.get('country_code'):item.update(country_code=f['country_code'],country_name=f.get('country_name',''),country_status='explicit_primary_page_location',country_missing_reason='')
        affs.append(item)
       au.append(author(a['name'],affs,**{k:a[k] for k in ('position','author_type','evidence_locator','affiliations_missing_reason') if k in a}))
      apply_auth(o,au,evs,'manual_primary_source_ordered');o['dedup_identifiers']={k:v for k,v in m.get('identity',{}).items() if k in ('doi','arxiv_id','openreview_id') and v and (ids.get(k)==v or m.get('primary_source_url'))} if not m.get('unverified_dedup') else {}
      o['unlinked_affiliations']=m.get('unlinked_affiliations',[])
      o['contributors']=m.get('contributors',[])
      if o['unlinked_affiliations']:
       o['institutions']=unique(o['institutions']+[a['name'] for a in o['unlinked_affiliations']]);o['field_provenance']['institutions']=evidence_field(o['institutions'],evs,'present_with_unlinked_affiliations')
      for k,v in m.get('identity',{}).items():
       if k in ('doi','arxiv_id','openreview_id') and v:
        o[k]=v;o['field_provenance'][k]=evidence_field(v,evs,'reported_supplement_identifier_not_dedup_eligible')
      for field in o['dedup_identifiers']:o['field_provenance'][field]=evidence_field(o[field],evs)
      for field in ('publication_date','version_date','date_type'):
       if m.get(field):o[field]=m[field]
      if o['version_date']:o['field_provenance']['version_date']=evidence_field(o['version_date'],evs)
      if o['publication_date']:
       o['date_precision']='day' if len(o['publication_date'])==10 else 'month' if len(o['publication_date'])==7 else 'year';o['field_provenance']['publication_date']=evidence_field(o['publication_date'],evs)
      o['warnings']+=m.get('notes',[]) if isinstance(m.get('notes'),list) else ([m['notes']] if m.get('notes') else [])
   yield o

def metric_row(rows):
 n=len(rows);a=sum(len(r['authors']) for r in rows);out={'source_occurrences':n,'ordered_author_slots':a}
 for f in FIELDS:
  k=sum(bool(r.get(f)) for r in rows);out[f]={'present':k,'denominator':n,'percent':round(100*k/n,3) if n else None}
 for k in ('affiliation_author_count','publication_time_affiliation_author_count','country_author_count'):
  num=sum(r.get(k,0) for r in rows);out[k]={'present':num,'denominator':a,'percent':round(num/a*100,3) if a else None}
 out['paper_scoped_institution_papers']=sum(any(f['temporal_status']=='paper_scoped_explicit' for a in r['authors'] for f in a['affiliations']) for r in rows)
 out['paper_reported_unlinked_institution_papers']=sum(bool(r.get('unlinked_affiliations')) for r in rows)
 out['unverified_time_institution_papers']=sum(any(f['temporal_status']=='publication_time_unverified' for a in r['authors'] for f in a['affiliations']) for r in rows)
 out['date_precision']=dict(collections.Counter(r.get('date_precision') or 'missing' for r in rows))
 out['field_status_counts']={f:dict(collections.Counter(r['field_provenance'][f]['status'] for r in rows)) for f in FIELDS}
 return out

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--conferences-root',type=Path,required=True);ap.add_argument('--original39-root',type=Path);ap.add_argument('--original39-supplement',type=Path);ap.add_argument('--output-dir',type=Path,required=True);ap.add_argument('--gzip',action='store_true',help='Compress JSONL output; always writes coverage and provenance JSON');ap.add_argument('--patch-only',action='store_true',help='Skip duplicate full JSONL and compact CSV; write the portable patch, coverage, and source evidence');args=ap.parse_args()
 b=args.conferences_root.resolve();out=args.output_dir;out.mkdir(parents=True,exist_ok=True);roots={'conferences':b}
 if args.original39_root:roots['original39']=args.original39_root.resolve()
 sources=Sources(roots);sources.manifests(b);idx=RawIndex(b,sources);idx.build();rows=[];baseline=[]
 for group,rel in [('ml','ml/metadata_main.jsonl'),('nlp_vision','nlp_vision/papers_main.jsonl'),('systems_ir','systems_ir/combined_papers.jsonl')]:
  p=b/rel
  if not p.exists():raise SystemExit('Missing required normalized input: '+str(p))
  for i,r in enumerate(jlread(p),1):rows.append(enrich(r,p,i,group,idx,sources));baseline.append({'venue':r['venue'],'year':r['year'],'authors':bool(r.get('authors')),'institutions':bool(r.get('institutions') or r.get('affiliations')),'countries':bool(r.get('countries')),'doi':bool(r.get('doi')),'openreview_id':bool(r.get('openreview_id')),'arxiv_id':bool(r.get('arxiv_id')),'publication_date':bool(r.get('publication_date')),'abstract':bool(r.get('abstract'))})
 if args.original39_root:rows.extend(original_rows(roots['original39'],args.original39_supplement,sources))
 # Exact-ID connected components only; preserve every source occurrence.
 parent=list(range(len(rows)));owner={};conflicts=[]
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,r in enumerate(rows):
  for k,v in r['dedup_identifiers'].items():
   key=(k,v)
   if key in owner:
    x,y=find(i),find(owner[key]);parent[max(x,y)]=min(x,y)
   else:owner[key]=i
 groups=collections.defaultdict(list)
 for i in range(len(rows)):groups[find(i)].append(i)
 for indexes in groups.values():
  identities=collections.defaultdict(set)
  for i in indexes:
   for k,v in rows[i]['dedup_identifiers'].items():identities[k].add(v)
  conflict=any(len(v)>1 for v in identities.values())
  key='paper:'+hashlib.sha256('\0'.join(sorted(rows[i]['occurrence_id'] for i in indexes)).encode()).hexdigest()[:24]
  if conflict:conflicts.append({'occurrences':[rows[i]['occurrence_id'] for i in indexes],'identifiers':{k:sorted(v) for k,v in identities.items()}})
  for i in indexes:rows[i]['paper_entity_id']=key;rows[i]['entity_identifier_conflict']=conflict
 dest=out/('metadata_enriched.jsonl.gz' if args.gzip else 'metadata_enriched.jsonl')
 if not args.patch_only:
  stream=io.TextIOWrapper(gzip.GzipFile(filename=str(dest),mode='wb',mtime=0),encoding='utf-8',newline='\n') if args.gzip else open(dest,'w',encoding='utf-8',newline='\n')
  with stream as f:
   for r in rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
 summary={'extractor_version':VERSION,'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'network_requests':0,'scope':'source occurrences preserved; unique entities use only source-validated exact identifiers','total':metric_row(rows),'conference_only':metric_row([r for r in rows if r['venue']!='Original39']),'unique_exact_id_entities':len(groups),'multi_occurrence_entities':sum(len(x)>1 for x in groups.values()),'identifier_conflicts':conflicts,'baseline_normalized':{'source_occurrences':len(baseline),'fields':{f:sum(r[f] for r in baseline) for f in FIELDS}},'by_venue':{v:metric_row([r for r in rows if r['venue']==v]) for v in sorted(set(r['venue'] for r in rows))},'by_venue_year':[{**{'venue':v,'year':y},**metric_row([r for r in rows if r['venue']==v and r['year']==y])} for v,y in sorted({(r['venue'],r['year']) for r in rows},key=lambda z:(z[0],z[1] or 0))],'raw_index_warnings':idx.warnings,'source_failures':sources.failures,'notes':['Program starttime is program_date, never publication_date.','Source institution labels are not canonical institution identities; multi-affiliation compound labels remain verbatim.','Country/region codes require explicit location tokens in paper-scoped affiliations; institutional headquarters and author names are never used.','ML and ICSE user-profile institution fields are publication_time_unverified and cannot supply historical countries.','Some existing normalized identifiers/abstracts came from upstream title joins; identifier dedup eligibility is separately recorded.','No paper is dropped because of missing authors, affiliations, countries or abstract.']}
 for name,data in [('coverage.json',summary),('source_manifest.json',{'sources':list(sources.entries.values())}),('examples.json',[r for v in sorted(set(r['venue'] for r in rows)) for r in [next((x for x in rows if x['venue']==v and x['institutions']),next(x for x in rows if x['venue']==v))]])]:
  (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Portable metadata patch omits duplicated title/abstract text; original normalized
 # inputs still own those fields. Every evidence ref resolves through source_manifest.
 patch_path=out/'metadata_patch.jsonl.gz'
 with io.TextIOWrapper(gzip.GzipFile(filename=str(patch_path),mode='wb',mtime=0),encoding='utf-8',newline='\n') as f:
  for r in rows:
   q={k:v for k,v in r.items() if k not in ('abstract','title','authors_raw')}
   q['field_provenance']=compact_provenance(r['field_provenance'])
   f.write(json.dumps(q,ensure_ascii=False,separators=(',',':'))+'\n')
 # Flat compact joinable file: JSON arrays remain fully escaped CSV fields.
 cols=['source_group','source_paper_id','occurrence_id','paper_entity_id','venue','year','track','title','official_url','authors','institutions','countries','doi','arxiv_id','openreview_id','publication_date','date_precision','date_type','program_date','dedup_identifiers','metadata_sidecar_ref']
 if not args.patch_only:
  with (out/'metadata_compact.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
   for r in rows:
    thin={**r,'authors':[a['name'] for a in r['authors']],'metadata_sidecar_ref':r['occurrence_id']}
    w.writerow({k:json.dumps(thin[k],ensure_ascii=False,separators=(',',':')) if isinstance(thin[k],(list,dict)) else thin[k] for k in cols})
 print(json.dumps({'records':len(rows),'unique_exact_id_entities':len(groups),'coverage':summary['total'],'output':str(out)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
