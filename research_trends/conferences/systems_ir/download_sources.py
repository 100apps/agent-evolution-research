"""Optional Windows-compatible refresh of public official sources. No arXiv API.
Reads sources_manifest.json. Existing snapshots remain intact; new files use .refresh suffix.
No bypass: 401/403/429 or anti-bot challenges are recorded and left for review.
"""
import pathlib,json,urllib.request,urllib.error,hashlib,datetime,time
P=pathlib.Path(__file__).resolve().parent
for s in json.loads((P/'sources_manifest.json').read_text(encoding='utf8')):
 if s.get('fetch_method')!='urllib_public_get':continue
 out={'url':s['url'],'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(s['url'],timeout=45) as r:body=r.read();out['status']=r.status
  if b'Making sure you' in body or b'Access Denied' in body:out['error']='Access challenge; no workaround attempted'
  else:
   f=P/(s['snapshot']+'.refresh');f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(body);out.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),snapshot=str(f.relative_to(P)))
 except Exception as e:out['error']=str(e)
 with open(P/'refresh_log.jsonl','a',encoding='utf8') as f:f.write(json.dumps(out)+'\n')
 print(out,flush=True);time.sleep(1)
