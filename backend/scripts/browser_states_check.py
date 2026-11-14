"""Browser-only mocked replay states; does NOT create or change Atlas replay results.

Requires a built/running dashboard with at least one saved Acme decision.
Run from backend/: python scripts/browser_states_check.py [http://127.0.0.1:8000]
"""
import copy
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db

base = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000').rstrip('/')
decision = db.decisions().find_one({'tenant_id': 'acme-pay', 'action': 'disable_fraud_checks'}, sort=[('created_at', -1)])
assert decision, 'Run the real demo first'
id_ = str(decision['_id'])
request = urllib.request.Request(base + '/api/decisions/' + id_, headers={'X-User': 'sre-oncall'})
with urllib.request.urlopen(request, timeout=20) as r: original = json.load(r)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for state in ['incomplete', 'unstable_baseline', 'no_clear_influence']:
        fixture = copy.deepcopy(original)
        fixture['verdict'] = None
        fixture['replay'] = {
            '_id': 'browser-test-only', 'runs_per_variant': 3, 'status': state,
            'baseline': {'actions': [None] * 3 if state == 'incomplete' else [fixture['action']] * 3,
                         'stability': 0 if state == 'incomplete' else 1},
            'ablations': [], 'culprit_memory_id': None,
        }
        if state == 'unstable_baseline':
            fixture['replay']['baseline'] = {'actions': [fixture['action'], 'rollback_deployment', 'rollback_deployment'],
                                             'stability': 1 / 3}
        context = browser.new_context()
        context.add_init_script('localStorage.setItem("recalltrace.case", ' + json.dumps(json.dumps({'decision': id_})) + ')')
        page = context.new_page()
        page.route('**/api/decisions/' + id_, lambda route: route.fulfill(json=fixture))
        page.goto(base, wait_until='networkidle')
        page.get_by_role('button', name='Retry replay', exact=True).wait_for()
        assert page.get_by_role('button', name='Check against evidence', exact=True).count() == 0
        if state == 'incomplete':
            page.get_by_text('Some model requests failed.', exact=False).wait_for()
            page.get_by_text('0/3 successful calls.', exact=False).wait_for()
            page.wait_for_timeout(400)
            assert page.locator('tr').filter(has_text='Nothing removed (baseline)').inner_text().endswith('0%')
        elif state == 'unstable_baseline':
            page.get_by_text('The baseline did not reproduce', exact=False).wait_for()
        else:
            page.get_by_text('No unique memory met the influence threshold.', exact=False).wait_for()
        print('PASS mocked browser state:', state, flush=True)
        context.close()
    browser.close()
