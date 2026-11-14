"""Pre-demo rehearsal: drives the brief's section 2 path against a RUNNING backend and checks each step.
LIVE: uses Atlas, Voyage, and the LLM, and RESETS the demo data first.

    uvicorn app.main:app --port 8000      # in another terminal
    python scripts/demo_check.py [http://localhost:8000]
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
TASK = ("Checkout API 5xx rate is 18% and rising. Fraud-check service p99 latency is 4.2s. "
        "Deploy v2.4.1 went out 10 minutes ago. Choose one action.")
failures = 0


def call(method, path, user=None, body=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-User": user} if user else {})})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read() or "null"), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, None, time.time() - t
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:  # server down, slow, or non-JSON
        print(f"     {method} {path}: {type(e).__name__}: {e}")
        return 0, None, time.time() - t


def check(label, ok, detail=""):
    global failures
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}  {detail}")
    return ok


code, body, dt = call("POST", "/api/demo/reset")
if not check("demo reset", code == 200, f"{body} {dt:.1f}s"):
    sys.exit(1)
time.sleep(3)  # let the search index pick up the fresh seed

code, d, dt = call("POST", "/api/run", "sre-oncall", {"task": TASK})
check("run 1 disables fraud checks", code == 200 and d["action"] == "disable_fraud_checks",
      f"{d and d['action']} fraud={d and d['sim_after']['fraud_rate']} {dt:.1f}s")
if code != 200:
    sys.exit(1)
stale = next((m for m in d["retrieved"] if m["text"].startswith("INC-212")), None)
if not check("stale INC-212 memory retrieved", stale is not None):
    sys.exit(1)  # every later step depends on it
check("expired deploy-freeze memory not retrieved", not any("deploy freeze" in m["text"] for m in d["retrieved"]))

check("contest", call("POST", f"/api/decisions/{d['_id']}/contest", "reviewer-dana", {"reason": "fraud red"})[0] == 200)
code, rp, dt = call("POST", f"/api/decisions/{d['_id']}/replay", "reviewer-dana")
check("replay culprit is INC-212", code == 200 and stale and rp["culprit_memory_id"] == stale["memory_id"],
      f"stable={rp and rp.get('stable')} {dt:.1f}s")
for a in (rp or {}).get("ablations", []):
    text = next(m["text"][:50] for m in d["retrieved"] if m["memory_id"] == a["removed_memory_id"])
    print(f"       flip {a['flip_rate']:.2f}  -{text}")

code, v, dt = call("POST", f"/api/decisions/{d['_id']}/verdict", "reviewer-dana")
check("verdict proposes a correction from PM-31", code == 200 and v["outcome"] == "correct"
      and v.get("evidence_title") == "Postmortem PM-31", f"{v and v['outcome']} {dt:.1f}s")
if code != 200:
    sys.exit(1)
code, a, _ = call("POST", f"/api/verdicts/{v['_id']}/approve", "reviewer-dana")
check("approve as reviewer-dana", code == 200 and a["approved_by"] == "reviewer-dana" and a["new_memory_id"])

mems = {m["_id"]: m for m in call("GET", "/api/memories", "sre-oncall")[1] or []}
old, new = mems.get(stale["memory_id"]), mems.get(a and a.get("new_memory_id"))
check("old memory quarantined and linked to new version",
      old and new and old["status"] == "quarantined" and old["superseded_by"] == new["_id"]
      and new["supersedes"] == old["_id"] and new["version"] == old["version"] + 1 and new["source_evidence_id"])

call("POST", "/api/sim/reset")
code, d2, dt = call("POST", "/api/run", "sre-oncall", {"task": TASK, "rerun_of": d["_id"]})
check("rerun rolls back", code == 200 and d2["action"] == "rollback_deployment",
      f"{d2 and d2['action']} fraud={d2 and d2['sim_after']['fraud_rate']} {dt:.1f}s")
check("rerun did not retrieve the quarantined memory",
      d2 and not any(m["memory_id"] == stale["memory_id"] for m in d2["retrieved"]))

code, res, _ = call("GET", f"/api/search?q={urllib.parse.quote(TASK)}", "platform-lee")
check("globex search returns only globex", code == 200 and res and all(r["tenant_id"] == "globex" for r in res),
      f"{len(res or [])} results")
check("globex direct read of acme memory refused", call("GET", f"/api/memories/{stale['memory_id']}", "platform-lee")[0] == 404)
log = call("GET", "/api/access-log", "platform-lee")[1] or []
check("refused read is in globex access log", any(not e["allowed"] for e in log))

print("PASS" if not failures else f"FAIL ({failures})")
sys.exit(1 if failures else 0)
