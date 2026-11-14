import argparse,json,time
parser=argparse.ArgumentParser(description='LIVE browser demo: resets demo data and uses real services')
parser.add_argument('--reset',action='store_true',required=True,help='Explicitly authorize replacing demo documents')
parser.add_argument('--base-url',default='http://127.0.0.1:8000')
args=parser.parse_args()
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=args.base_url.rstrip('/')
out=Path(__file__).resolve().parents[2]/'.local'/'qa'
out.mkdir(parents=True,exist_ok=True)
responses=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 context=browser.new_context(viewport={'width':1440,'height':960},record_video_dir=str(out/'raw'),record_video_size={'width':1440,'height':960})
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 def response(r):
  if '/api/' in r.url and r.request.method=='POST':
   try:responses.append({'path':r.url.split('/api/')[-1],'status':r.status,'data':r.json()})
   except Exception:pass
 page.on('response',response)
 page.goto(BASE,wait_until='networkidle')
 page.get_by_role('button',name='Reset demo',exact=True).click()
 page.get_by_role('button',name='Run agent',exact=True).wait_for(timeout=120000)
 page.get_by_role('button',name='Reset demo',exact=True).wait_for(timeout=120000)
 time.sleep(4)
 page.screenshot(path=str(out/'01-incident.png'))
 with page.expect_response(lambda r:r.url.endswith('/api/run') and r.request.method=='POST',timeout=120000) as pending:
  page.get_by_role('button',name='Run agent',exact=True).click()
 original=pending.value.json();assert pending.value.status==200 and original['action']=='disable_fraud_checks'
 page.get_by_role('button',name='Contest decision',exact=True).wait_for(timeout=15000)
 page.get_by_role('heading',name='Decision').evaluate('(el)=>el.scrollIntoView({block:"start"})')
 time.sleep(1);page.screenshot(path=str(out/'02-unsafe-decision.png'))
 print('PASS browser: real unsafe decision and fraud spike',flush=True)
 page.get_by_label('Session user').select_option('reviewer-dana')
 with page.expect_response(lambda r:r.url.endswith('/replay') and r.request.method=='POST',timeout=150000) as pending:
  page.get_by_role('button',name='Contest decision',exact=True).click()
 replay=pending.value.json();assert pending.value.status==200 and replay['stable'] and replay['culprit_memory_id']
 page.get_by_role('button',name='Check against evidence',exact=True).wait_for(timeout=15000)
 page.get_by_role('heading',name='Investigation').evaluate('(el)=>el.scrollIntoView({block:"start"})')
 time.sleep(1);page.screenshot(path=str(out/'03-replay.png'))
 print('PASS browser: repeated replay, stable baseline, influential memory',flush=True)
 with page.expect_response(lambda r:r.url.endswith('/verdict') and r.request.method=='POST',timeout=120000) as pending:
  page.get_by_role('button',name='Check against evidence',exact=True).click()
 verdict=pending.value.json();assert pending.value.status==200 and verdict['outcome']=='correct'
 page.get_by_role('button',name='Approve as reviewer-dana',exact=True).wait_for(timeout=15000)
 page.get_by_role('heading',name='Verdict').evaluate('(el)=>el.scrollIntoView({block:"start"})')
 time.sleep(1);page.screenshot(path=str(out/'04-evidence-review.png'))
 print('PASS browser: verified evidence and correction proposal',flush=True)
 with page.expect_response(lambda r:r.url.endswith('/approve') and r.request.method=='POST',timeout=120000) as pending:
  page.get_by_role('button',name='Approve as reviewer-dana',exact=True).click()
 approval=pending.value.json();assert pending.value.status==200 and approval['approved_by']=='reviewer-dana'
 page.get_by_role('button',name='Reset simulation and rerun',exact=True).wait_for(timeout=15000)
 with page.expect_response(lambda r:r.url.endswith('/api/run') and r.request.method=='POST',timeout=120000) as pending:
  page.get_by_role('button',name='Reset simulation and rerun',exact=True).click()
 rerun=pending.value.json();assert pending.value.status==200 and rerun['action']=='rollback_deployment'
 assert not any(m['memory_id']==replay['culprit_memory_id'] for m in rerun['retrieved'])
 assert any(m['memory_id']==approval['new_memory_id'] for m in rerun['retrieved'])
 page.get_by_text('Before',exact=True).wait_for(timeout=15000)
 page.get_by_role('heading',name='Rerun').evaluate('(el)=>el.scrollIntoView({block:"start"})')
 time.sleep(2);page.screenshot(path=str(out/'05-before-after.png'))
 print('PASS browser: approval, new retrieval, rollback and safer fraud rate',flush=True)
 page.get_by_label('Session user').select_option('platform-lee')
 assert page.get_by_role('heading',name='Decision').count()==0
 assert page.get_by_text(original['rationale'],exact=True).count()==0
 with page.expect_response(lambda r:'/api/search?' in r.url,timeout=30000) as pending:
  page.get_by_role('button',name='Search as globex',exact=True).click()
 hits=pending.value.json();assert pending.value.status==200 and hits and all(m['tenant_id']=='globex' for m in hits)
 page.get_by_role('button',name='Request memory',exact=True).click()
 page.get_by_text('404 not found',exact=True).wait_for(timeout=15000)
 assert page.get_by_text('allowed: false',exact=False).count()>0
 time.sleep(1);page.screenshot(path=str(out/'06-isolation.png'))
 print('PASS browser: tenant switch hides Acme decision, Globex search and logged refusal',flush=True)
 assert not errors,errors
 out.joinpath('browser-results.json').write_text(json.dumps({'errors':errors,'responses':responses,'original_id':original['_id'],'replay_id':replay['_id'],'verdict_id':verdict['_id'],'rerun_id':rerun['_id']},indent=2))
 context.close();browser.close()
print('PASS complete real browser walkthrough',flush=True)
