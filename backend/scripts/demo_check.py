"""Live API checks through FastAPI's in-process HTTP client (real Atlas/Voyage).

Run from backend/: python scripts/demo_check.py
Add --execute for a real LLM preflight followed by a fresh decision and replay.
No reset/reseed: normal access logs and, with --execute, decision/replay records are written.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import ObjectId
from fastapi.testclient import TestClient

from app import config, db, llm, main as api, sim
from app.prompts import ACTIONS, SYSTEM_PROMPT, TOOLS
from app.seed import TASK


class CheckFailed(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CheckFailed(message)


def check(execute=False):
    if execute:
        require(config.LLM_PROVIDER and config.LLM_MODEL and config.LLM_API_KEY,
                'Configure LLM_PROVIDER, LLM_MODEL, and LLM_API_KEY first')
        # Check billing before retrieving or writing any demo data.
        result = llm.decide(SYSTEM_PROMPT, TASK, [], TOOLS, llm.default_model())
        require(result['action'] in ACTIONS, 'LLM returned an unknown tool')
        print('PASS real LLM structured tool call', flush=True)

    with TestClient(api.app) as client:
        acme = {'X-User': 'sre-oncall'}
        globex = {'X-User': 'platform-lee'}
        response = client.get('/api/health')
        require(response.status_code == 200, 'Health endpoint failed')
        index = response.json()['indexes'][db.MEMORY_INDEX]
        require(index and index['queryable'], 'Memory vector index is not queryable')
        print('PASS live Atlas health and memory-index readiness', flush=True)

        require(client.get('/api/memories').status_code == 422, 'Missing session header was accepted')
        require(client.get('/api/memories', headers={'X-User': 'unknown'}).status_code == 401,
                'Unknown session user was accepted')
        print('PASS missing/unknown session checks', flush=True)

        memories = {}
        for tenant, headers in [('acme-pay', acme), ('globex', globex)]:
            response = client.get('/api/memories', headers=headers)
            require(response.status_code == 200, f'{tenant} memory listing failed')
            memories[tenant] = response.json()
            require(memories[tenant] and all(m['tenant_id'] == tenant for m in memories[tenant]),
                    f'{tenant} memory listing was empty or leaked data')
            require(all('embedding' not in m for m in memories[tenant]), 'Memory listing exposed embedding arrays')
        print('PASS tenant-specific memory lists', flush=True)

        memory_id = memories['acme-pay'][0]['_id']
        require(client.get(f'/api/memories/{memory_id}', headers=globex).status_code == 404,
                'Cross-tenant memory read was accepted')
        log = client.get('/api/access-log', headers=globex).json()
        require(any(e['kind'] == 'get' and e['query'] == memory_id and not e['allowed'] for e in log),
                'Cross-tenant refusal was not logged')
        print('PASS cross-tenant direct-read refusal and access log', flush=True)

        for tenant, headers in [('acme-pay', acme), ('globex', globex)]:
            response = client.get('/api/search', params={'q': TASK}, headers=headers)
            require(response.status_code == 200, f'{tenant} live search failed')
            hits = response.json()
            require(hits and all(h['tenant_id'] == tenant and h['status'] == 'active' for h in hits),
                    f'{tenant} search was empty or returned ineligible memories')
            print(f'PASS live Voyage/Atlas search as {tenant}: {len(hits)} results', flush=True)

        original = db.decisions().find_one({'tenant_id': 'acme-pay', 'action': 'disable_fraud_checks'},
                                          sort=[('created_at', 1)])
        if original:
            decision_id = str(original['_id'])
            response = client.get(f'/api/decisions/{decision_id}', headers=acme)
            require(response.status_code == 200, 'Stored decision retrieval failed')
            saved = response.json()
            require(saved['_id'] == decision_id and saved['tenant_id'] == 'acme-pay', 'Stored decision mismatch')
            for field in ['replay', 'verdict']:
                if saved[field]:
                    require(saved[field]['decision_id'] == decision_id, f'Stored {field} trace mismatch')
            require(client.get(f'/api/decisions/{decision_id}', headers=globex).status_code == 404,
                    'Cross-tenant decision read was accepted')
            require(client.post(f'/api/decisions/{decision_id}/replay', headers=globex).status_code == 404,
                    'Cross-tenant replay was accepted')
            print('PASS stored decision/replay/verdict serialization and decision tenant guard', flush=True)
        else:
            print('SKIP stored bad-decision check: none exists; no history was fabricated', flush=True)

        if execute:
            response = client.post('/api/run', headers=acme, json={'task': TASK})
            require(response.status_code == 200, 'Fresh agent decision failed')
            decision = response.json()
            require(decision['action'] in ACTIONS and decision['retrieved'], 'Fresh decision lacked a tool or memories')
            require(db.decisions().find_one({'_id': ObjectId(decision['_id']), 'tenant_id': 'acme-pay'}) is not None,
                    'Fresh decision was not stored in Atlas')
            before = sim.get()
            response = client.post(f"/api/decisions/{decision['_id']}/replay", headers=acme)
            require(response.status_code == 200, 'Fresh replay endpoint failed')
            require(sim.get() == before, 'Replay changed simulator state')
            replay = response.json()
            require(replay['decision_id'] == decision['_id'] and replay['tenant_id'] == 'acme-pay',
                    'Fresh replay trace mismatch')
            require(replay['status'] != 'incomplete', 'Replay has failed LLM trials; inspect its errors')
            require(db.replays().find_one({'_id': ObjectId(replay['_id'])}) is not None,
                    'Fresh replay was not stored in Atlas')
            print(f"PASS fresh action={decision['action']}; replay status={replay['status']}; simulator unchanged by replay",
                  flush=True)
            require(replay['stable'], 'Fresh replay baseline was unstable; repeat and inspect variability')
            print('Current active memories were used; no action or influential memory was forced.', flush=True)

    print('PASS live API checks' + (' including fresh LLM decision/replay' if execute else ' (no fresh LLM run)'),
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Make real LLM calls and store one new decision/replay')
    args = parser.parse_args()
    try:
        check(args.execute)
    except CheckFailed as exc:
        print('FAIL:', exc, flush=True)
        return 1
    except Exception as exc:
        # Never dump provider responses, request headers, connection strings, or keys.
        print('BLOCKED:', type(exc).__name__, flush=True)
        status = getattr(exc, 'status_code', None)
        if status is not None:
            print('HTTP status:', status, flush=True)
        code = getattr(exc, 'code', None)
        if code in {'credit_balance_exhausted', 'insufficient_quota', 'rate_limit_exceeded',
                    'invalid_api_key', 'model_not_found'}:
            print('Provider code:', code, flush=True)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
