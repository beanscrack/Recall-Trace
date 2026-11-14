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
| C1 | Teammate 1: correction | Tighten evidence eligibility | Partial: verified_by filter merged; service relevance and unavailable-index fallback still need review |
| C2 | Teammate 1: correction | Verify correction approval and failure handling | Partial: transactional approval implementation merged and existing Atlas correction verified; team reports live approval passed, but injected transaction-failure checks remain untested here |
| F1 | Teammate 2: frontend | Replace mock data with API responses | Merged in PR #1: live dashboard controls and API wiring; current frontend build/lint passed |
| F2 | Teammate 2: frontend | Show replay status and before/after behavior | Merged: replay status, measured flip rates, correction and before/after panels; team reports browser walkthrough passed |
| F3 | Teammate 2: frontend | Wire tenant isolation panel | Merged: live search, direct-read refusal, and access-log panel; live API tenant guards passed |
| D1 | All three | Rehearse complete live demo | Team reports full Anthropic rehearsal passed; Super VL flip gate, live decision/replay, and correction draft passed here; full Super VL approval/rerun rehearsal remains |
| D2 | All three | Prepare submission | Open: accessible demo, public repo, one-minute video with audio, description, team members, event sandbox eligibility |
| G1 | Repository owner | Update GitHub About settings | Repository rename confirmed: `beanscrack/Recall-Trace`; About description/topics remain owner-managed |

Seeding replaces demo documents. Existing Atlas data includes decisions, replay, and verdict records, so do not reset it as part of a connectivity check. Run the backend as one worker because the simulator remains process-local.

## Verified in this workspace

- 22 offline checks passed: replay/API (15), Atlas setup readiness (2), DNS configuration (3), failed-agent behavior (2).
- Live application Atlas ping and real Voyage document/query embeddings passed.
- Both vector indexes are READY/queryable with 1024-dimensional vector fields.
- Six live retrieval cases returned only eligible same-tenant memories; both direct-read refusal checks were logged.
- Existing approved correction links, version increment, active/quarantined states, embedding dimensions, and reviewer metadata passed inspection.
- Stored decisions show an unsafe action followed by a rollback rerun, but fresh LLM execution now passes with OpenRouter Nemotron 3.5 Super VL; direct OpenAI remains blocked by its API credit balance.
- No collections were reset or reseeded. Live retrieval tests added their normal access-log entries.

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
