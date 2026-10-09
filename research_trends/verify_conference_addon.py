#!/usr/bin/env python3
"""Read-only portable package verification. Python 3.10+, standard library, offline."""
from pathlib import Path,PurePosixPath
from html.parser import HTMLParser
import argparse,json,gzip,hashlib,csv,collections,base64,zipfile,re

def sha(b):return hashlib.sha256(b).hexdigest()
def safe(name):
 p=PurePosixPath(name)
 return bool(name) and not p.is_absolute() and all(v not in ('','..','.') for v in name.split('/')) and '\\' not in name and ':' not in name
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.fragments=[];self.assets=[];self.figures=0;self.svg=0;self.downloads=[];self.scripts=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if a.get('href','').startswith('#'):self.fragments.append(a['href'][1:])
  if tag=='figure':self.figures+=1
  if tag=='svg':self.svg+=1
  if tag=='script':self.scripts+=1
  if tag in ('img','script','iframe','link') and (a.get('src') or a.get('href')):self.assets.append(a.get('src',a.get('href')))
  if a.get('href','').startswith('data:'):
   header,data=a['href'].split(',',1);assert ';base64' in header
   b=base64.b64decode(data,validate=True);assert b;self.downloads.append({'name':a.get('download'),'bytes':len(b),'sha256':sha(b)})
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--zip',type=Path,help='Optionally verify an archive without extracting it');ap.add_argument('--check-base',action='store_true',help='Also require exact ML, NLP/CV and restored extra corpus inputs');a=ap.parse_args()
 root=Path(__file__).resolve().parent
 manifest=json.loads((root/'CONFERENCE_ADDON_MANIFEST.json').read_text(encoding='utf-8'))
 for r in manifest['files']:
  assert safe(r['path']),r['path'];p=root/r['path'];assert p.resolve().is_relative_to(root)
  b=p.read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
 c=root/'conferences';s=c/'systems_ir';rm=json.loads((s/'restore_manifest.json').read_text(encoding='utf-8'));b=gzip.decompress((s/'combined_papers.jsonl.gz').read_bytes())
 assert len(b)==rm['uncompressed_bytes'] and sha(b)==rm['uncompressed_sha256']
 rows=[json.loads(l) for l in b.splitlines() if l.strip()]
 assert len(rows)==6193 and len({(x['venue'],x['year'],x['stable_id']) for x in rows})==6193
 assert all(x['main_research'] is True and x['title'].strip() for x in rows)
 counts=dict(sorted(collections.Counter(x['venue'] for x in rows).items()));assert counts==rm['venue_counts']
 source_hashes={x['sha256'] for x in json.loads((s/'sources_manifest.json').read_text(encoding='utf-8'))}
 system_hashes={v for x in json.loads((s/'systems/sources_manifest.json').read_text(encoding='utf-8')) for v in x['sha256'].values()}
 assert all((x.get('source_sha256') in source_hashes) if x.get('source_sha256') else (bool(x.get('source_hashes')) and set(x['source_hashes'].values())<=system_hashes) for x in rows)
 p=c/'audit';fm=json.loads((p/'sampling_frame_manifest.json').read_text(encoding='utf-8'));fb=gzip.decompress((p/'sampling_frame.jsonl.gz').read_bytes());assert sha(fb)==fm['uncompressed_sha256']
 frame=[json.loads(l) for l in fb.splitlines()];assert len(frame)==2557 and sum(bool(x['abstract'].strip()) for x in frame)==2543
 sample=json.loads((p/'audit_sample_unlabeled.json').read_text(encoding='utf-8'));labels=json.loads((p/'agent_abstract_audit.json').read_text(encoding='utf-8'));summary=json.loads((p/'audit_summary.json').read_text(encoding='utf-8'))
 assert len(sample)==len(labels)==60 and len({x['paper_id'] for x in labels})==60
 for x,y in zip(sample,labels):
  assert x['paper_id']==y['paper_id'] and y['evidence_quote'] in x['abstract'] and len(y['evidence_quote'].split())<=25
  assert sha(x['abstract'].encode())==y['abstract_sha256'] and abs(y['inclusion_probability']*y['inverse_probability_weight']-1)<1e-10
 assert collections.Counter(x['category'] for x in labels)==summary['unweighted_sample_counts']
 assert abs(sum(x['inverse_probability_weight'] for x in labels)-2543)<1e-8
 with (c/'comparison/coverage_common.csv').open(encoding='utf-8-sig',newline='') as f:coverage=list(csv.DictReader(f))
 assert sum(int(x['n_records']) for x in coverage if x['n_records'])==89530
 with (c/'comparison/venue_year_topic_counts.csv').open(encoding='utf-8-sig',newline='') as f:
  for x in csv.DictReader(f):assert 0<=int(x['count'])<=int(x['denominator']) and abs(float(x['share_pct'])-100*int(x['count'])/int(x['denominator']))<1e-9
 text=(root/'reports/conference_supplement.html').read_text(encoding='utf-8');html=Page();html.feed(text)
 assert html.figures==html.svg==9 and len(html.ids)==len(set(html.ids)) and set(html.fragments)<=set(html.ids)
 assert not html.assets and not html.scripts and not re.search(r'url\s*\(',text,re.I)
 assert len(html.downloads)==14
 monthly=root/'reports/conference_supplement_data/monthly/arxiv_monthly_library_extracted.csv'
 with monthly.open(encoding='utf-8-sig',newline='') as f:months=list(csv.DictReader(f))
 assert len(months)==81 and months[0]['month']=='2020-01' and months[-1]['month']=='2026-09'
 if a.check_base:
  for x in json.loads((c/'comparison/source_corpus_manifest.json').read_text(encoding='utf-8'))['source_files']:assert sha((c/x['relative_path']).read_bytes())==x['sha256'],x['relative_path']
 zip_info=None
 if a.zip:
  with zipfile.ZipFile(a.zip) as z:
   names=z.namelist();assert len(names)==len(set(names));assert all(safe(n) and n.startswith('research_trends/') for n in names)
   assert all(not ((i.external_attr>>16)&0o170000)==0o120000 for i in z.infolist()),'Symlink member'
   assert z.testzip() is None
   expected={'research_trends/'+x['path']:x for x in manifest['files']}
   assert set(names)==set(expected)|{'research_trends/CONFERENCE_ADDON_MANIFEST.json'}
   for n,r in expected.items():assert sha(z.read(n))==r['sha256'] and len(z.read(n))==r['bytes']
   assert z.read('research_trends/CONFERENCE_ADDON_MANIFEST.json')==(root/'CONFERENCE_ADDON_MANIFEST.json').read_bytes()
   zip_info={'bytes':a.zip.stat().st_size,'sha256':sha(a.zip.read_bytes()),'members':len(names),'crc_and_safe_paths':'PASS'}
 print(json.dumps({'result':'PASS','manifest_files':len(manifest['files']),'metadata_records':len(rows),'venue_counts':counts,'audit_frame_positive':len(frame),'audit_frame_eligible':2543,'audit_sample_n':60,'comparison_records':89530,'html_figures':html.figures,'html_downloads':len(html.downloads),'monthly_rows':len(months),'visual_browser_qa':'NOT RUN; previous Chromium socket-creation restriction remains documented','zip':zip_info},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
