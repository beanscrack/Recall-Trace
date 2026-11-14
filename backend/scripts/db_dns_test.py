"""Offline checks for the opt-in Atlas DNS override. Run from backend/."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db


class DatabaseDnsTest(unittest.TestCase):
    def setUp(self):
        db.get_db.cache_clear()
        self.addCleanup(db.get_db.cache_clear)

    def test_override_configures_dns_before_client_creation(self):
        resolver = Mock()
        nameservers = ["1.1.1.1", "1.0.0.1"]
        def client(*args, **kwargs):
            self.assertEqual(resolver.nameservers, nameservers)
            return {"test_db": "database"}
        with patch.object(config, "MONGODB_URI", "mongodb+srv://example.invalid/"), \
             patch.object(config, "MONGODB_DB", "test_db"), \
             patch.object(config, "MONGODB_DNS_NAMESERVERS", nameservers), \
             patch.object(db.dns.resolver, "get_default_resolver", return_value=resolver), \
             patch.object(db, "MongoClient", side_effect=client) as create:
            self.assertEqual(db.get_db(), "database")
            self.assertEqual(db.get_db(), "database")
            self.assertEqual(create.call_count, 1)

    def test_blank_override_preserves_system_dns(self):
        with patch.object(config, "MONGODB_URI", "mongodb://example.invalid/"), \
             patch.object(config, "MONGODB_DNS_NAMESERVERS", []), \
             patch.object(db.dns.resolver, "get_default_resolver") as resolver, \
             patch.object(db, "MongoClient"):
            db.get_db()
            resolver.assert_not_called()

    def test_missing_uri_fails_before_dns_or_connection(self):
        with patch.object(config, "MONGODB_URI", ""), \
             patch.object(db.dns.resolver, "get_default_resolver") as resolver, \
             patch.object(db, "MongoClient") as client:
            with self.assertRaisesRegex(RuntimeError, "MONGODB_URI is not set"):
                db.get_db()
            resolver.assert_not_called()
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
