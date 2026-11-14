# RecallTrace demo tasks

Owners reflect the team's original assignments; this checklist does not establish who is currently online or what is unpushed. Keep tasks updated as results are verified.

| ID | Owner | Task | Status / acceptance |
| --- | --- | --- | --- |
| B1 | Us: backend / replay | Make Atlas DNS workaround available to the application | Done: optional `MONGODB_DNS_NAMESERVERS` configured locally; fresh-process application ping and three offline DNS checks passed |
| B2 | Us: backend / replay | Inspect sandbox data and indexes without reseeding | Done: connection passed; both 1024-dimensional vector indexes are READY and queryable; existing demo records preserved |
| B3 | Us: backend / replay | Verify real Voyage embeddings | Done: document and query embeddings each returned 1024 dimensions |
| B4 | Us: backend / replay | Validate live retrieval, expiry, quarantine, and tenant boundaries | Done: six live nonempty searches passed tenant/status/expiry checks; both cross-tenant direct reads were refused and logged (Voyage paced at 21-second intervals) |
| B5 | Us: backend / replay | Run real LLM decision and replay using current code | Done with OpenRouter nvidia/nemotron-3.5-super-vl:free: real tool call, flip gate 5/5 both ways, fresh Atlas-backed decision/replay, and forced correction draft passed |
| B6 | Us: backend / replay | Verify live API integration and failed-agent behavior | Done: real Atlas/Voyage API checks passed; stored decision/replay/verdict serialization and tenant guards passed; failure regression tests confirm no tool execution or decision write |
| C1 | Backend / correction | Tighten evidence eligibility | Done: explicit same-service/newer/verified eligibility, exact canonical legacy-seed compatibility, safe handling of unknown legacy text, and deliberate unavailable-index fallback; offline and live tests passed |
| C2 | Backend / correction | Verify correction approval and failure handling | Done: real Atlas rollback after injected insert/verdict failures and atomic success; temporary test fixtures removed |
| F1 | Frontend | Live dashboard and API integration | Done: complete real-browser workflow passed over the public HTTPS tunnel |
| F2 | Frontend | Replay failure states and before/after display | Done: failed calls are not shown as flips, status explanations and retry added; three mocked browser states passed separately from real workflow |
| F3 | Frontend | Tenant isolation panel | Done: real browser tenant switch hides Acme content; Globex search and logged refusal passed |
| D1 | All three | Complete Super VL live demo rehearsal | Done: HTTP and public-browser paths passed through correction, named approval, and rollback rerun |
| D2 | All three | Submission materials | Prepared: one-minute narrated video, description, run evidence, and public demo. Final team details, Sandbox invitation confirmation, and submission deferred by user |
| D3 | Backend / hosting | Accessible demo and deployment preparation | Done as requested: verified temporary public tunnel; one-origin production serving, Dockerfile, and Render blueprint prepared. Docker image build untested because engine is unavailable |
| G1 | Repository owner | Update GitHub About settings | Owner action remains: connected account cannot administer repository. Exact description/topics and owner command prepared in DEPLOYMENT.md |

Seeding replaces demo documents. Existing Atlas data includes decisions, replay, and verdict records, so do not reset it as part of a connectivity check. Run the backend as one worker because the simulator remains process-local.

## Verified in this workspace

- 34 offline checks passed, including evidence fallback, query-vector cache isolation, and seed-failure preservation.
- Live application Atlas ping and real Voyage document/query embeddings passed.
- Both vector indexes are READY/queryable with 1024-dimensional vector fields.
- Six live retrieval cases returned only eligible same-tenant memories; both direct-read refusal checks were logged.
- Existing approved correction links, version increment, active/quarantined states, embedding dimensions, and reviewer metadata passed inspection.
- Stored decisions show an unsafe action followed by a rollback rerun, but fresh LLM execution now passes with OpenRouter Nemotron 3.5 Super VL; direct OpenAI remains blocked by its API credit balance.
- Initial non-destructive checks preserved data; full rehearsals later intentionally reset/reseeded the demo after an owner-readable local backup. Temporary live-test fixtures were removed.

## Repeatable checks

Run from `backend/`:

```bash
.venv/bin/python -m unittest discover -s scripts -p "*_test.py" -v
.venv/bin/python scripts/demo_check.py
# With the configured OpenRouter model:
.venv/bin/python scripts/flip_test.py
.venv/bin/python scripts/demo_check.py --execute
```

`demo_check.py` uses real Atlas/Voyage through FastAPI in-process HTTP requests. Default mode checks health, session headers, tenant memory lists/search, logged refusal, and stored decision/replay/verdict responses. `--execute` first checks the real LLM before any retrieval/write, then creates a new decision/replay using current active memories and checks persistence and unchanged simulator state during replay. It does not reset/reseed data or force an action/culprit. Exit codes: 0 passed, 1 failed assertion, 2 external/configuration blockage.

## Nemotron 3.5 Super VL validation

On 2026-11-14, configured the ignored local `.env` for `nvidia/nemotron-3.5-super-vl:free` at `https://openrouter.ai/api/v1` using the existing OpenAI-compatible adapter. No key was committed.

- A real structured decision call passed.
- Fixed-input flip gate: 5/5 `disable_fraud_checks` with the stale memory; 5/5 `rollback_deployment` without it.
- `demo_check.py --execute` passed live Atlas/Voyage HTTP checks and saved a fresh `rollback_deployment` decision with its replay. That run used current corrected memories and reported `no_clear_influence`; its baseline was stable, and replay did not change simulator state.
- A separate real forced `submit_review` call detected the stale-memory contradiction and returned nonempty corrected text. This test did not approve or alter memories.
- All 22 offline checks, frontend production build, and frontend lint passed on the merged team code.
- No reset/reseed was performed by these checks. This is not a claim that a full Super VL correction-approval-rerun rehearsal has passed.

## Completion evidence

See [VALIDATION.md](VALIDATION.md) for the final real-service/browser results and [DEPLOYMENT.md](DEPLOYMENT.md) for the temporary live URL, video, hosting recipe, and owner-only GitHub metadata action. Submission details remain deferred; no external competition submission is claimed.

The shared dataset was later reset by another process using old seeds. Compatibility was added only for exact canonical seed/key/tenant/text matches; unknown or changed legacy text still cannot inherit a service. The full no-reseed legacy rehearsal passed, including actual corrected-memory retrieval. Its measured run is archived separately in `docs/submission/legacy-seed-run.json`.
