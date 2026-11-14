"""Run cross-tenant-ish queries as each tenant and assert nothing from the other tenant comes back.
Requires seeded data. Run from backend/: python scripts/isolation_check.py
For Voyage's 3 RPM tier, add --interval 21 after letting previous requests age out.
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.retrieval import get_memory, search_memories  # noqa: E402
from app.seed import TASK  # noqa: E402

CASES = {
    ("globex", "platform-lee"): [TASK, "disable fraud checks runbook INC-212",
                                 "how long does a checkout-api rollback take", "Risk team fraud-check owner"],
    ("acme-pay", "sre-oncall"): ["scale the fraud-check pool to 12 replicas",
                                 "failover to the backup processor from the ops console"],
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--interval", type=float, default=0, help="Seconds between embedding requests")
args = parser.parse_args()
if args.interval < 0:
    parser.error("--interval must be nonnegative")

failures = 0
last_request = None
for (tenant, user), queries in CASES.items():
    for q in queries:
        if last_request is not None:
            time.sleep(max(0, args.interval - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        docs = search_memories(tenant, user, q)
        leaked = [d for d in docs if d["tenant_id"] != tenant]
        now = datetime.now(timezone.utc)
        ineligible = [d for d in docs if d["status"] != "active" or
                      d["expires_at"].replace(tzinfo=timezone.utc) <= now]
        ok = bool(docs) and not leaked and not ineligible
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {tenant:<9} {len(docs)} results; "
              f"leaked={len(leaked)} ineligible={len(ineligible)}  {q[:60]}")
    other = db.memories().find_one({"tenant_id": {"$ne": tenant}}, {"_id": 1})
    if other is None:
        failures += 1
        print(f"FAIL {tenant:<9} no other-tenant memory available to test refusal")
        continue
    refused = get_memory(tenant, user, str(other["_id"])) is None
    logged = db.access_log().find_one({"tenant_id": tenant, "user_id": user, "kind": "get",
                                     "query": str(other["_id"]), "allowed": False}) is not None
    failures += not (refused and logged)
    print(f"{'ok  ' if refused and logged else 'FAIL'} {tenant:<9} "
          f"direct read of other tenant's memory refused={refused} logged={logged}")

print("PASS" if failures == 0 else f"FAIL ({failures})")
sys.exit(1 if failures else 0)
