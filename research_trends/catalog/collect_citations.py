#!/usr/bin/env python3
"""Capped, resumable free OpenAlex DOI-batch citation snapshot collector.

Only exact DOI keys already verified in the master CSV are requested. No key,
account, paid endpoint, title search, or cross-source score aggregation.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "agent-evolution-research/1.0 (public reproducibility; no credentials)"
SELECT = "id,doi,cited_by_count,counts_by_year,updated_date,is_retracted"

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def batches(dois: list[str]):
    batch = []
    for doi in dois:
        test = batch + [doi]
        url = "https://api.openalex.org/works?" + urlencode({"filter": "doi:" + "|".join("https://doi.org/" + x for x in test),
                                                        "per_page": 100, "select": SELECT})
        if batch and (len(test) > 100 or len(url) > 7000):
            yield batch
            batch = [doi]
        else:
            batch = test
    if batch:
        yield batch

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--max-calls", type=int, default=1)
    ap.add_argument("--min-remaining-credits", type=int, default=100)
    ap.add_argument("--min-interval-seconds", type=float, default=1.6)
    args=ap.parse_args()
    if args.max_calls < 1 or args.max_calls > 120:
        raise SystemExit("max-calls must be between 1 and 120")
    dois=set()
    with args.master.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            if row["doi"]:
                dois.add(row["doi"].lower())
    groups=list(batches(sorted(dois)))
    output=args.output_dir.resolve()
    raw=output/"raw"
    raw.mkdir(parents=True,exist_ok=True)
    audit=output/"query_audit.jsonl"
    done={}
    if audit.exists():
        for line in audit.read_text(encoding="utf-8").splitlines():
            x=json.loads(line)
            if x.get("http_status")==200 and (raw/(x["query_sha256"]+".json")).is_file():
                body=(raw/(x["query_sha256"]+".json")).read_bytes()
                if digest(body)==x["raw_sha256"]:
                    done[x["query_sha256"]]=x
    used=0
    last=0.0
    for i, group in enumerate(groups):
        url="https://api.openalex.org/works?"+urlencode({"filter":"doi:"+"|".join("https://doi.org/"+x for x in group),
                                                          "per_page":100,"select":SELECT})
        key=digest(url.encode())
        if key in done:
            continue
        if used >= args.max_calls:
            break
        delay=args.min_interval_seconds-(time.monotonic()-last)
        if delay>0:time.sleep(delay)
        when=datetime.now(timezone.utc).isoformat()
        try:
            with urlopen(Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json"}),timeout=30) as response:
                status=response.status
                body=response.read(6_000_000)
                headers=response.headers
        except HTTPError as error:
            status=error.code;body=error.read(100_000);headers=error.headers
        except (URLError,TimeoutError) as error:
            status=0;body=str(error).encode();headers={}
        last=time.monotonic();used+=1
        record={"at_utc":when,"batch_index":i,"doi_count":len(group),"url":url,
                "query_sha256":key,"http_status":status,"raw_sha256":digest(body),
                "response_bytes":len(body),
                "rate_limit_remaining":headers.get("X-RateLimit-Remaining", ""),
                "rate_limit_credits_used":headers.get("X-RateLimit-Credits-Used", ""),
                "meta_cost":None}
        if status==200:
            try:
                decoded=json.loads(body)
                record["meta_cost"]=(decoded.get("meta") or {}).get("cost")
                record["result_count"]=len(decoded.get("results") or [])
            except ValueError:
                record["http_status"]=0
            (raw/(key+".json")).write_bytes(body)
        with audit.open("a",encoding="utf-8",newline="\n") as f:
            f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
        print(json.dumps({k:record[k] for k in ("batch_index","doi_count","http_status","result_count","rate_limit_remaining","rate_limit_credits_used") if k in record}))
        if status!=200:
            break  # preserve failure; never treat as zero or silently retry
        remaining=record["rate_limit_remaining"]
        if remaining and int(remaining)<args.min_remaining_credits:
            break
        if record["rate_limit_credits_used"] and int(record["rate_limit_credits_used"])>1:
            break  # avoid unexpectedly expensive read queries
    print(json.dumps({"verified_doi_keys":len(dois),"planned_batches":len(groups),"new_calls":used,
                      "cached_successes":len(done),"audit":str(audit)},ensure_ascii=False))

if __name__=="__main__":main()
