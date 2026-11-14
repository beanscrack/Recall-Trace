"""LIVE Atlas transaction checks with temporary, isolated test fixtures.

Run from backend/: python scripts/court_transaction_check.py
Embeddings are mocked; MongoDB transactions and rollback are real. Temporary
fixtures use a unique test tenant and are removed even after an assertion fails.
No real demo memories, decisions, replays, or verdicts are modified.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bson import ObjectId
from app import court, db


def main():
    database = db.get_db()
    tenant = 'transaction-check-' + uuid4().hex
    vector = [1.] + [0.] * 1023
    now = datetime.now(timezone.utc)
    memory_id, verdict_id = ObjectId(), ObjectId()
    memory = {'_id': memory_id, 'tenant_id': tenant, 'service': 'checkout', 'text': 'Synthetic test fixture',
              'status': 'active', 'version': 1, 'created_at': now,
              'expires_at': datetime(2099, 1, 1, tzinfo=timezone.utc), 'embedding': vector,
              'supersedes': None, 'superseded_by': None}
    verdict = {'_id': verdict_id, 'tenant_id': tenant, 'memory_id': memory_id, 'status': 'proposed',
               'outcome': 'correct', 'proposed_text': 'Synthetic corrected fixture', 'evidence_id': ObjectId(),
               'new_memory_id': None, 'approved_by': None, 'approved_at': None}
    try:
        database.memories.insert_one(memory)
        database.verdicts.insert_one(verdict)

        # Normal-query fallback still requires the same service, a newer date,
        # and a real verifier. Deliberately omit an embedding from this lookup.
        base = {'tenant_id': tenant, 'text': 'Synthetic evidence fixture',
                'created_at': now + timedelta(seconds=1), 'service': 'checkout', 'verified_by': 'test-reviewer'}
        candidates = [dict(base), {**base, 'service': 'cart'}, {**base, 'verified_by': '   '},
                      {**base, 'created_at': now - timedelta(days=1)}]
        evidence_ids = database.evidence.insert_many(candidates).inserted_ids
        lookup = {k: v for k, v in memory.items() if k != 'embedding'}
        matched = court.find_evidence(lookup)
        assert matched and matched['_id'] == evidence_ids[0]
        database.evidence.delete_one({'_id': evidence_ids[0]})
        assert court.find_evidence(lookup) is None
        print('PASS live evidence fallback excludes wrong-service, unverified, and older records', flush=True)

        def unchanged():
            old = database.memories.find_one({'_id': memory_id})
            saved = database.verdicts.find_one({'_id': verdict_id})
            assert old['status'] == 'active' and old['superseded_by'] is None
            assert database.memories.count_documents({'tenant_id': tenant}) == 1
            assert saved['status'] == 'proposed' and saved['new_memory_id'] is None

        with patch.object(court, 'embed', side_effect=RuntimeError('injected embedding failure')):
            try: court.approve_verdict(str(verdict_id), 'test-reviewer')
            except RuntimeError: pass
            else: raise AssertionError('Embedding failure was not propagated')
        unchanged()
        print('PASS embedding failure leaves original memory and verdict unchanged', flush=True)

        real_memories, real_verdicts = database.memories, database.verdicts
        class InsertFailure:
            def __getattr__(self, name): return getattr(real_memories, name)
            def insert_one(self, *args, **kwargs): raise RuntimeError('injected insert failure')
        with patch.object(court, 'embed', return_value=[vector]), \
             patch.object(court.db, 'memories', return_value=InsertFailure()):
            try: court.approve_verdict(str(verdict_id), 'test-reviewer')
            except RuntimeError: pass
            else: raise AssertionError('Insert failure was not propagated')
        unchanged()
        print('PASS Atlas rollback after quarantine and failed replacement insert', flush=True)

        class VerdictFailure:
            def __getattr__(self, name): return getattr(real_verdicts, name)
            def update_one(self, *args, **kwargs): raise RuntimeError('injected verdict failure')
        with patch.object(court, 'embed', return_value=[vector]), \
             patch.object(court.db, 'verdicts', return_value=VerdictFailure()):
            try: court.approve_verdict(str(verdict_id), 'test-reviewer')
            except RuntimeError: pass
            else: raise AssertionError('Verdict failure was not propagated')
        unchanged()
        print('PASS Atlas rollback after replacement insert/link and failed verdict update', flush=True)

        with patch.object(court, 'embed', return_value=[vector]):
            result = court.approve_verdict(str(verdict_id), 'test-reviewer')
        old = database.memories.find_one({'_id': memory_id})
        new = database.memories.find_one({'_id': result['new_memory_id']})
        assert old['status'] == 'quarantined' and old['superseded_by'] == new['_id']
        assert new['supersedes'] == memory_id and new['version'] == 2 and new['service'] == 'checkout'
        assert result['status'] == 'approved' and result['approved_by'] == 'test-reviewer'
        assert database.verdicts.find_one({'_id': verdict_id})['status'] == 'approved'
        print('PASS atomic commit: quarantine, replacement, version/service links, and approval', flush=True)
    finally:
        database.memories.delete_many({'tenant_id': tenant})
        database.verdicts.delete_many({'tenant_id': tenant})
        database.evidence.delete_many({'tenant_id': tenant})
        assert database.memories.count_documents({'tenant_id': tenant}) == 0
        assert database.verdicts.count_documents({'tenant_id': tenant}) == 0
        assert database.evidence.count_documents({'tenant_id': tenant}) == 0
        print('Temporary transaction fixtures removed', flush=True)


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print('FAIL:', type(exc).__name__)
        sys.exit(1)
