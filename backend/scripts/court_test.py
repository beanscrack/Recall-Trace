"""Offline evidence eligibility and embedding-cache checks. Run via unittest discovery."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymongo.errors import OperationFailure
from app import court, embeddings, seed


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.memory = {'tenant_id': 'acme-pay', 'service': 'checkout',
                       'created_at': datetime(2026, 2, 10, tzinfo=timezone.utc), 'embedding': [1., 0.]}
        self.coll = Mock()
        self.coll.list_search_indexes.return_value = []
        self.coll.find_one.return_value = {'title': 'verified same-service evidence'}
        p = patch.object(court.db, 'evidence', return_value=self.coll)
        p.start(); self.addCleanup(p.stop)

    def test_fallback_requires_tenant_service_newer_and_nonblank_verifier(self):
        court.find_evidence(self.memory)
        query = self.coll.find_one.call_args.args[0]
        self.assertEqual(query['tenant_id'], 'acme-pay')
        self.assertEqual(query['service'], 'checkout')
        self.assertEqual(query['created_at'], {'$gt': self.memory['created_at']})
        self.assertEqual(query['verified_by'], {'$type': 'string', '$regex': r'\S'})
        self.coll.aggregate.assert_not_called()

    def test_untagged_legacy_memory_does_not_guess_service(self):
        self.memory.pop('service')
        self.assertIsNone(court.find_evidence(self.memory))
        self.coll.find_one.assert_not_called()
        self.coll.list_search_indexes.assert_not_called()

    def test_building_index_uses_eligible_normal_query(self):
        self.coll.list_search_indexes.return_value = [{'name': court.EVIDENCE_INDEX, 'queryable': False}]
        court.find_evidence(self.memory)
        self.coll.aggregate.assert_not_called()
        self.coll.find_one.assert_called_once()

    def test_vector_hit_uses_same_rules_as_fallback(self):
        self.coll.list_search_indexes.return_value = [{'name': court.EVIDENCE_INDEX, 'queryable': True}]
        self.coll.aggregate.return_value = iter([{'title': 'matched'}])
        self.assertEqual(court.find_evidence(self.memory), {'title': 'matched'})
        pipeline = self.coll.aggregate.call_args.args[0]
        match = next(stage['$match'] for stage in pipeline if '$match' in stage)
        self.assertEqual(match['service'], 'checkout')
        self.assertEqual(match['tenant_id'], 'acme-pay')
        self.assertIn('verified_by', match)
        self.coll.find_one.assert_not_called()

    def test_removed_index_falls_back(self):
        self.coll.list_search_indexes.return_value = [{'name': court.EVIDENCE_INDEX, 'queryable': True}]
        self.coll.aggregate.side_effect = OperationFailure('index removed', code=27)
        court.find_evidence(self.memory)
        self.coll.find_one.assert_called_once()

    def test_permission_error_is_not_disguised_as_no_evidence(self):
        self.coll.list_search_indexes.side_effect = OperationFailure('unauthorized', code=13)
        with self.assertRaises(OperationFailure): court.find_evidence(self.memory)
        self.coll.find_one.assert_not_called()

    def test_empty_vector_result_uses_same_service_fallback(self):
        self.coll.list_search_indexes.return_value = [{'name': court.EVIDENCE_INDEX, 'queryable': True}]
        self.coll.aggregate.return_value = iter([])
        court.find_evidence(self.memory)
        self.assertEqual(self.coll.find_one.call_args.args[0]['service'], 'checkout')


class EmbeddingCacheTest(unittest.TestCase):
    def setUp(self):
        embeddings._query_vector.cache_clear()
        self.addCleanup(embeddings._query_vector.cache_clear)

    def test_repeated_query_uses_one_embedding_and_returns_isolated_lists(self):
        with patch.object(embeddings, 'embed', return_value=[[1., 2.]]) as embed:
            first = embeddings.embed_query('same incident')
            first[0] = 99.
            self.assertEqual(embeddings.embed_query('same incident'), [1., 2.])
            embed.assert_called_once_with(['same incident'], input_type='query')

    def test_failure_is_not_cached(self):
        with patch.object(embeddings, 'embed', side_effect=[RuntimeError(), [[1.]]]) as embed:
            with self.assertRaises(RuntimeError): embeddings.embed_query('incident')
            self.assertEqual(embeddings.embed_query('incident'), [1.])
            self.assertEqual(embed.call_count, 2)


class SeedFailureTest(unittest.TestCase):
    def test_embedding_failure_preserves_existing_demo(self):
        with patch.object(seed, 'embed', side_effect=RuntimeError('Voyage unavailable')), \
             patch.object(seed.db, 'ensure_collections') as ensure, \
             patch.object(seed.db, 'get_db') as get_db:
            with self.assertRaises(RuntimeError): seed.reset()
            ensure.assert_not_called()
            get_db.assert_not_called()


if __name__ == '__main__': unittest.main(verbosity=2)
