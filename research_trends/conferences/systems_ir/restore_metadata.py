#!/usr/bin/env python3
"""Restore the exact frozen 6,193-paper metadata offline. Refuse conflicting files."""
from pathlib import Path
import gzip,hashlib,json,argparse,os

def main():
 p=Path(__file__).resolve().parent
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=p/'combined_papers.jsonl');a=ap.parse_args()
 m=json.loads((p/'restore_manifest.json').read_text(encoding='utf-8'))
 compressed=(p/'combined_papers.jsonl.gz').read_bytes()
 if hashlib.sha256(compressed).hexdigest()!=m['compressed_sha256']:raise SystemExit('Compressed payload checksum mismatch')
 b=gzip.decompress(compressed)
 if hashlib.sha256(b).hexdigest()!=m['uncompressed_sha256'] or len(b)!=m['uncompressed_bytes']:raise SystemExit('Restored metadata checksum mismatch')
 rows=[json.loads(x) for x in b.splitlines() if x.strip()]
 if len(rows)!=6193:raise SystemExit('Unexpected record count')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():
  if a.output.read_bytes()!=b:raise SystemExit('Refusing to overwrite different existing metadata. Choose a new --output path.')
  print('Already restored: 6,193 records; SHA-256 verified.');return
 # Exclusive creation prevents an accidental overwrite or a check/write race.
 with a.output.open('xb') as f:f.write(b)
 print('Restored 6,193 records; exact bytes and SHA-256 verified: '+str(a.output))
if __name__=='__main__':main()
