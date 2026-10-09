#!/usr/bin/env python3
"""Rebuild OSDI/SOSP bibliographic dataset from archived official source snapshots.
Uses only Python standard library. Run from any cwd; outputs adjacent to script.
USENIX snapshots are web-tool rendered text, not HTML (direct fetch was blocked).
SOSP snapshots are official HTML. HTML comments are removed before extraction.
"""
from pathlib import Path
from collections import Counter
import json, re, html, hashlib, unicodedata, csv, shutil
from urllib.parse import urljoin
P=Path(__file__).resolve().parent
DATE='2026-10-09'

def norm(x):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',x).lower())
def clean(x):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',x))).strip()
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
# Deliberately explicit, conservative title-only signals. These are not a census
# of papers using AI: training/inference/agents/GPU alone are intentionally absent.
LLM=re.compile(r'\b(?:LLMs?|large language models?|language models?|generative AI|generative artificial intelligence|retrieval[- ]augmented generation|RAG|ChatGPT|GPT[- ]?\d*|BERT)\b',re.I)
AI=re.compile(r'\b(?:artificial intelligence|AI|machine learning|ML|deep learning|neural(?:[- ]networks?)?|DNNs?|CNNs?|GNNs?|federated learning|reinforcement learning|deep graph learning|graph learning|invariant learning|learning[- ](?:based|augmented)|learned|neuro[- ]symbolic)\b',re.I)
TOCS={2020:'osdi20__contents.pdf',2021:'osdi21-contents.pdf',2022:'osdi22__contents.pdf',2023:'osdi23_contents.pdf',2024:'osdi24_contents.pdf',2025:'osdi25-contents.pdf',2026:'osdi26-contents.pdf'}
rows=[];sources=[];audit=[]

def finish(r):
 r['field']='computer_systems'
 r['traditional_domain']=True
 r['abstract']=None
 r['retrieved_date_utc']=DATE
 r['id']=r['conference'].lower()+str(r['year'])+'-'+hashlib.sha256(norm(r['title']).encode()).hexdigest()[:16]
 r['llm_title_matches']=list(dict.fromkeys(m[0] for m in LLM.finditer(r['title'])))
 r['ai_title_matches']=list(dict.fromkeys(m[0] for m in AI.finditer(r['title'])))
 r['llm_title_marker']=bool(r['llm_title_matches'])
 r['ai_title_marker']=bool(r['ai_title_matches'] or r['llm_title_matches'])
 r['classification_basis']='conservative_explicit_title_markers_v1'
 rows.append(r)

for y in range(2020,2027):
 url=f'https://www.usenix.org/conference/osdi{y%100:02d}/technical-sessions'
 toc_url='https://www.usenix.org/sites/default/files/'+TOCS[y]
 lines={};toc={};snapshots=[]
 for f in sorted(P.glob(f'osdi{y}_sessions_*_web.json')):
  snapshots.append(f.name)
  for n,t in re.findall(r'(?:^|\s)L(\d+): (.*?)(?=\sL\d+: |\Z)',json.loads(f.read_text()),re.S):lines[int(n)]=t.strip()
 for f in sorted(P.glob(f'osdi{y}_toc*web.json')):
  for n,t in re.findall(r'^L(\d+)@P[\d-]+: (.*)$',json.loads(f.read_text()),re.M):toc[int(n)]=t
 all_toc=norm(' '.join(toc[k] for k in sorted(toc)))
 assert lines and toc
 # All title-bearing region lines must be captured; the last footer is irrelevant.
 assert not(set(range(max(lines)+1))-set(lines)),(y,'missing session lines')
 assert not(set(range(max(toc)+1))-set(toc)),(y,'missing toc lines')
 session=None;excluded=[]
 for n,t in sorted(lines.items()):
  m=re.match(r'## cite(\d+)†(.*?)',t)
  if not m:
   if t.startswith('## '):session=t[3:]
   continue
  title=m[2]
  if norm(title) not in all_toc:
   excluded.append(title);continue # Keynotes/invited talks absent from proceedings TOC.
  title_raw=title
  track='operational_systems' if title.endswith(' (Operational Systems)') else 'research'
  if track=='operational_systems':title=title[:-len(' (Operational Systems)')]
  # The authors are the first prose block after title and before media/award text.
  authors=[]
  started=False
  for j in range(n+1,min(n+9,max(lines)+1)):
   x=lines[j]
   if not x:
    if started:break
    continue
   if x.startswith(('Available Media','Awarded ','Distinguished ','Operational Systems Paper','#')):break
   started=True;authors.append(x)
  finish(dict(conference='OSDI',year=y,title=title,title_as_source=title_raw,authors_text=' '.join(authors),track=track,main_research=(track=='research'),session=session,source_url=url,url=url,url_kind='official_program_page',proceedings_toc_url=toc_url,doi=None,source_line=n,source_format='web_tool_rendered_text'))
 audit.append(dict(conference='OSDI',year=y,program_title_count=sum(bool(re.match(r'## cite\d+†',x)) for x in lines.values()),excluded_nonpaper_titles=excluded,accepted_paper_count=sum(r['conference']=='OSDI' and r['year']==y for r in rows),captured_line_min=min(lines),captured_line_max=max(lines),toc_line_count=len(toc),title_membership_check='Every included title occurs in normalized official proceedings TOC'))
 sources.append(dict(conference='OSDI',year=y,url=url,secondary_validation_url=toc_url,fetch_method='web.run open; direct HTTP access was unavailable and not retried',snapshots=snapshots,toc_snapshots=[f.name for f in sorted(P.glob(f'osdi{y}_toc*web.json'))]))

for y in [2021,2023,2024,2025,2026]:
 f=P/f'sosp{y}.html'
 if not f.exists():shutil.copyfile(P.parent/'raw'/f.name,f)
 url=f'https://sosp{y}.mpi-sws.org/accepted.html' if y in [2021,2023] else f'https://sigops.org/s/conferences/sosp/{y}/accepted.html'
 raw=f.read_text();s=re.sub(r'<!--.*?-->','',raw,flags=re.S)
 if y in [2021,2023]:
  data=re.findall(r'<p>\s*<b>(.*?)</b>\s*by\s*(.*?)</p>',s,re.S|re.I)
  bcount=len(re.findall(r'<b>.*?</b>\s*by\s*',s,re.S|re.I))
 else:
  ul='\n'.join(re.findall(r'<ul class="paperlist">(.*?)</ul>',s,re.S|re.I))
  data=re.findall(r'<b>(.*?)</b>\s*(?:<br\s*/?>)?\s*<em>(.*?)</em>',ul,re.S|re.I)
  bcount=len(re.findall(r'<b\b',ul,re.I))
  licount=len(re.findall(r'<li\b',ul,re.I))
  assert len(data)==licount,(y,len(data),licount)
 assert len(data)==bcount,(y,len(data),bcount)
 for title,authors in data:
  finish(dict(conference='SOSP',year=y,title=clean(title),title_as_source=clean(title),authors_text=clean(authors),track='research',main_research=True,session=None,source_url=url,url=url,url_kind='official_accepted_list',proceedings_toc_url=None,doi=None,source_format='official_html'))
 audit.append(dict(conference='SOSP',year=y,accepted_paper_count=len(data),bold_title_count=bcount,comments_removed=True,parser_note='Case-insensitive tags; optional br between title and authors; exactly one row per visible paperlist li for 2024 onward.'))
 sources.append(dict(conference='SOSP',year=y,url=url,fetch_method='Python urllib public official URL',snapshots=[f.name]))

# Enrich stable paper-level links from official proceedings/program pages.
# These explicit accepted-to-final-title aliases were inspected individually.
ALIASES={
 (2021,norm('IODA: A Host/Device Co-Design for Strong Predictability Contract on Modern Flash Storage')):'lODA: A Host/Device Co-Design for Strong Predictability Contract on Modern Flash Storage',
 (2021,norm('The Demikernel Library OS Architecture for Microsecond, Kernel-Bypass Datacenter Systems')):'The Demikernel Datapath OS Architecture for Microsecond-scale Datacenter Systems',
 (2021,norm('When Idling is Ideal: Optimizing Tail-Latency for Highly-Dispersed Datacenter Workloads with Perséphone')):'When Idling is Ideal: Optimizing Tail-Latency for Heavy-Tailed Datacenter Workloads with Perséphone',
 (2024,norm('Efficient file-lifetime redundancy management for cluster file systems')):'Morph: Efficient File-Lifetime Redundancy Management for Cluster File Systems',
 (2024,norm('NOPE: Strengthening domain authentication with zero-knowledge proofs')):'NOPE: Strengthening Domain Authentication with Succinct Proofs',
 (2024,norm('ReCycle: Pipeline Adaptation for the Resilient Distributed Training of Large DNNs')):'ReCycle: Resilient Training of Large DNNs using Pipeline Adaptation',
 (2024,norm('VPRI: Optimized I/O Page Fault in Public IaaS')):'VPRI: Efficient I/O Page Fault Handling via Software-Hardware Co-Design for IaaS Clouds',
}
for y in [2021,2023,2024,2025,2026]:
 name=f'sosp{y}_toc.html' if y in [2021,2023] else f'sosp{y}_schedule.html'
 f=P/name
 if not f.exists():continue
 url=f'https://sigops.org/s/conferences/sosp/{y}/'+('toc.html' if y in [2021,2023] else 'schedule.html')
 s=re.sub(r'<!--.*?-->','',f.read_text(),flags=re.S)
 aa=re.findall(r'<a\b[^>]*href=[\"\x27]([^\"\x27]+)[\"\x27][^>]*>(.*?)</a>',s,re.S|re.I)
 aa=[(u,clean(t)) for u,t in aa if 'dl.acm.org' in u or '.pdf' in u]
 if y==2026:aa=[(u,clean(t)) for t,u in re.findall(r'<li>([^<]*?)\[<a href="(https://dl.acm.org/doi/[^"]+)">paper</a>',s,re.S)]
 mp={norm(t):(urljoin(url,u),t) for u,t in aa}
 matched=0
 for r in rows:
  if r['conference']!='SOSP' or r['year']!=y:continue
  key=norm(ALIASES.get((y,norm(r['title'])),r['title']))
  if key in mp:
   r['url'],r['published_title']=mp[key]
   r['paper_link_source_url']=url
   r['url_kind']='doi_landing_page' if 'dl.acm.org/doi/' in r['url'] else 'official_paper_pdf'
   if r['url_kind']=='doi_landing_page':r['doi']=r['url'].split('/doi/')[-1]
   matched+=1
 sources.append(dict(conference='SOSP',year=y,url=url,fetch_method='Python urllib public official URL',snapshots=[name],purpose='paper-level link enrichment',matched_accepted_titles=matched))

for r in rows:
 if r['conference']=='SOSP' and r['year']==2025 and r['title'].startswith('Analyzing and Enhancing ArckFS:'):
  r['doi']='10.1145/3731569.3768291'
  r['url']='https://doi.org/'+r['doi']
  r['url_kind']='doi_landing_page'
  r['published_title']=r['title']
  r['pages']='1149-1157'
  r['page_count']=9
  r['paper_link_source_url']='https://pure.kaist.ac.kr/en/publications/analyzing-and-enhancing-arckfs-an-anecdotal-example-of-benefits-o/'
  r['author_hosted_pdf_url']='https://rs3lab.github.io/assets/papers/2025/jeon:arckfsfix.pdf'
  r['scope_note']='Included in the official accepted-paper list and main proceedings. No separate short-paper track designation established; specific regular-review process not verified.'
sources.append(dict(conference='SOSP',year=2025,url='https://pure.kaist.ac.kr/en/publications/analyzing-and-enhancing-arckfs-an-anecdotal-example-of-benefits-o/',secondary_validation_url='https://rs3lab.github.io/assets/papers/2025/jeon:arckfsfix.pdf',fetch_method='web.run open',snapshots=['sosp2025_arckfs_verified_metadata_web.json'],purpose='Verify DOI, main proceedings, pages 1149-1157, and 9-page length of ArckFS contribution'))
sources.append(dict(conference='OSDI',year=2026,url='https://www.usenix.org/sites/default/files/osdi26-message.pdf',fetch_method='web.run open',snapshots=['osdi2026_chairs_web.json'],purpose='Validate 136 program papers, 19 Operational Systems, acceptance and format change'))
sources.append(dict(conference='OSDI',year=2026,url='https://www.usenix.org/conference/osdi26/call-for-papers',fetch_method='web.run open',snapshots=['osdi2026_scope_validation_web.json'],purpose='Document 2026 review-process and scope changes'))
ids=[r['id'] for r in rows];assert len(ids)==len(set(ids)), 'duplicate records'
rows.sort(key=lambda r:(r['conference'],r['year'],r['title'].lower()))
(P/'systems_papers.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
(P/'systems_research_papers.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows if r['main_research']))
(P/'parse_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
for source in sources:
 source['retrieved_date_utc']=DATE
 source['sha256']={name:sha(P/name) for name in source['snapshots']+source.get('toc_snapshots',[])}
(P/'sources_manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
summary=[]
for conf in ['OSDI','SOSP']:
 for y in range(2020,2027):
  for scope in ['research_only','all_main_program']:
   rr=[r for r in rows if r['conference']==conf and r['year']==y and (scope=='all_main_program' or r['main_research'])]
   if not rr:continue
   summary.append(dict(conference=conf,year=y,scope=scope,n=len(rr),ai_title_marked=sum(r['ai_title_marker'] for r in rr),llm_title_marked=sum(r['llm_title_marker'] for r in rr)))
(P/'summary_counts.json').write_text(json.dumps(summary,indent=2)+'\n')
with (P/'summary_counts.csv').open('w') as out:
 writer=csv.DictWriter(out,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
print(json.dumps({'records_all_main':len(rows),'records_research':sum(r['main_research'] for r in rows),'summary':summary},indent=2))
