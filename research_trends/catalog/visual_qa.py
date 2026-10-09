#!/usr/bin/env python3
"""Real Edge desktop/mobile smoke test of the built static Explorer."""
from __future__ import annotations
import argparse,functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--site-dir',type=Path,required=True)
 ap.add_argument('--output-dir',type=Path,required=True)
 args=ap.parse_args()
 site=args.site_dir.resolve();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(site))
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 url=f'http://127.0.0.1:{server.server_port}/research-trends/explorer/'
 results={};errors=[]
 try:
  with sync_playwright() as playwright:
   browser=playwright.chromium.launch(channel='msedge',headless=True)
   for label,width,height in [('desktop',1440,900),('mobile',390,844)]:
    page=browser.new_page(viewport={'width':width,'height':height},accept_downloads=True)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(url,wait_until='domcontentloaded',timeout=60000)
    page.wait_for_function("document.querySelector('#loadStatus')?.textContent?.includes('筛选完成')",timeout=90000)
    summary=page.locator('#summary').inner_text()
    if '84,008' not in summary:raise AssertionError(f'{label} default provisional exclusion failed: {summary}')
    if page.locator('#tableBody tr').count()!=50:raise AssertionError('pagination did not show 50 rows')
    overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
    if overflow:
     offenders=page.evaluate("[...document.querySelectorAll('*')].filter(e=>!e.closest('.table-wrap')&&!e.closest('.cross')).map(e=>({tag:e.tagName,id:e.id,cls:e.className?.toString()?.slice(0,35),right:Math.round(e.getBoundingClientRect().right),width:Math.round(e.getBoundingClientRect().width)})).filter(x=>x.right>innerWidth+2).slice(0,30)")
     print(json.dumps({'overflow':label,'document_width':page.evaluate('document.documentElement.scrollWidth'),'offenders':offenders},ensure_ascii=False))
     page.screenshot(path=str(out/f'{label}-overflow.png'),full_page=True)
     raise AssertionError(f'{label} document overflows viewport')
    page.screenshot(path=str(out/f'{label}.png'),full_page=True)
    if label=='desktop':
     page.locator('#provisional').check()
     page.wait_for_function("document.querySelector('#summary')?.textContent?.includes('89,530')",timeout=30000)
     page.locator('#provisional').uncheck()
     page.locator('#yearMin').select_option('2024')
     page.locator('#yearMax').select_option('2024')
     page.locator('#sort').select_option('citations')
     page.wait_for_function("document.querySelectorAll('#tableBody tr').length>0 && [...document.querySelectorAll('#tableBody tr')].every(tr=>tr.querySelector('td')?.textContent==='2024')",timeout=30000)
     page.locator('#country').select_option('CN')
     page.wait_for_function("document.querySelector('#loadStatus')?.textContent?.includes('筛选完成') && new URL(location.href).searchParams.get('country')==='CN'",timeout=30000)
     country_summary=page.locator('#summary').inner_text()
     page.locator('#country').select_option('')
     results['country_filter_summary']=country_summary
    results[label]={'default_rows':84008,'page_rows':50,'document_overflow':False}
    page.close()
   browser.close()
 finally:server.shutdown();server.server_close()
 if errors:raise AssertionError(f'JavaScript errors: {errors[:3]}')
 receipt={'passed':True,'url':url,'results':results,'page_errors':errors}
 (out/'qa_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
