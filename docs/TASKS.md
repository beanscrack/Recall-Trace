# RecallTrace demo tasks

Owners reflect the team's original assignments; this checklist does not establish who is currently online or what is unpushed. Keep tasks updated as results are verified.

| ID | Owner | Task | Status / acceptance |
| --- | --- | --- | --- |
| B1 | Us: backend / replay | Make Atlas DNS workaround available to the application | Done: optional `MONGODB_DNS_NAMESERVERS` configured locally; fresh-process application ping and three offline DNS checks passed |
| B2 | Us: backend / replay | Inspect sandbox data and indexes without reseeding | Done: connection passed; both 1024-dimensional vector indexes are READY and queryable; existing demo records preserved |
| B3 | Us: backend / replay | Verify real Voyage embeddings | Done: document and query embeddings each returned 1024 dimensions |
| B4 | Us: backend / replay | Validate live retrieval, expiry, quarantine, and tenant boundaries | Done: six live nonempty searches passed tenant/status/expiry checks; both cross-tenant direct reads were refused and logged (Voyage paced at 21-second intervals) |
| B5 | Us: backend / replay | Run real LLM decision and replay using current code | Waiting for local model/key and custom base URL if applicable; provider set to OpenAI-compatible; offline replay tests pass |
| C1 | Teammate 1: correction | Tighten evidence eligibility | Open: require verified evidence about the same service; handle unavailable evidence index deliberately |
| C2 | Teammate 1: correction | Verify correction approval and failure handling | Partial: existing Atlas correction verified (quarantine, replacement, links, version, embedding dimensions, reviewer); fresh approval and failure handling remain untested |
| F1 | Teammate 2: frontend | Replace mock data with API responses | Open on main: Run, Contest, Replay, Verdict, Approve, Reset, Rerun; handle loading and failures |
| F2 | Teammate 2: frontend | Show replay status and before/after behavior | Open: unstable/incomplete/tied cases, actual flip rates, outcomes, and correction history |
| F3 | Teammate 2: frontend | Wire tenant isolation panel | Open: use GET /api/search and the direct-read refusal/access log; clear previous tenant's displayed data on switch |
| D1 | All three | Rehearse complete live demo | Open: original decision -> replay -> approval -> fresh retrieval -> changed action -> tenant isolation |
| D2 | All three | Prepare submission | Open: accessible demo, public repo, one-minute video with audio, description, team members, event sandbox eligibility |
| G1 | Repository owner | Update GitHub About settings | Repository rename confirmed: `beanscrack/Recall-Trace`; About description/topics remain owner-managed |

Seeding replaces demo documents. Existing Atlas data includes decisions, replay, and verdict records, so do not reset it as part of a connectivity check. Run the backend as one worker because the simulator remains process-local.

## Verified in this workspace

- 20 offline checks passed: replay/API (15), Atlas setup readiness (2), DNS configuration (3).
- Live application Atlas ping and real Voyage document/query embeddings passed.
- Both vector indexes are READY/queryable with 1024-dimensional vector fields.
- Six live retrieval cases returned only eligible same-tenant memories; both direct-read refusal checks were logged.
- Existing approved correction links, version increment, active/quarantined states, embedding dimensions, and reviewer metadata passed inspection.
- Stored decisions show an unsafe action followed by a rollback rerun, but fresh LLM execution in this workspace is still waiting for credentials.
- No collections were reset or reseeded. Live retrieval tests added their normal access-log entries.
