# Agents in Context Toronto — track alignment

RecallTrace targets **Statement Two: Memory You Can Govern** at **Agents in Context Toronto: a MongoDB Hackathon**, November 14, 2026.

This mapping follows the supplied event resource guide. It distinguishes implemented behavior from eligibility or submission details that require organizer/account confirmation.

| Track requirement | Implementation | Evidence |
| --- | --- | --- |
| Atlas and Vector Search persist and retrieve memory | Six Atlas collections; Voyage document/query embeddings; `$vectorSearch` in `retrieval.py` | Live retrieval and both vector indexes verified |
| Memory changes the next action | Approved replacement is retrieved in the same incident's next run | Validated disable-fraud-checks → rollback demonstration |
| Rules for who can read memories | Session-derived tenant filters inside Vector Search; scoped direct reads | Live Globex search and logged Acme read refusal; identity picker is a demo mechanism |
| Rules for memory lifetime | `expires_at` and `status` filters, plus live-field rechecks for index lag | Expired/quarantined memories excluded during validation |
| Corrections are governed | Newer, same-tenant/service, verified evidence; named human approval | Atomic quarantine/replacement/version-link transaction and failure-injection rollback tests |
| Explain memory influence | Original decision snapshot; repeated baseline and individual-removal tool comparisons | Stable 3/3 baseline and 3/3 action changes for stale-memory removal in the recorded run |
| Public source and accessible demo | Public GitHub and temporary app/video links | Links provided in README; keep the tunnel and backend running |
| Event Atlas Sandbox | Application connects to Atlas; invitation provenance is not visible in code | Team must confirm event-issued project/cluster creation before claiming eligibility |

## Why Atlas and Voyage matter

Voyage turns query and memory text into embeddings. Atlas Vector Search retrieves semantically relevant memories while applying governance filters. Atlas also preserves exact decision context, actual replay outcomes, approved versions, and access events. Correcting a memory changes what fresh retrieval can return.

Replay intentionally does not re-query current memories: it uses the recorded snapshot and never executes tool actions. Similarity scores do not prove influence; repeated tool-choice comparisons provide evidence of influence, not mathematical causation.

The default context is up to four memories, with three calls per replay variant. Pairwise investigation remains an optional backend feature and is excluded from the current demo UI. See [PAIRWISE_REPLAY.md](PAIRWISE_REPLAY.md).

## Resources versus required runtime technologies

Atlas and Vector Search are central to the selected track; Voyage is our embedding provider. MongoDB MCP configuration is included as an optional development aid. Agent Skills, LangGraph, LangSmith, ElevenLabs, and change streams are not claimed as implemented runtime dependencies. Adding every partner technology is not necessary to explain this track's memory-governance loop.

## Submission materials

The event guide requests a public repository, a one-minute video showing code and functionality, a concise description, and all team members added in Cerebral Valley. It specifies original work, teams of up to four, and an event-issued Atlas Sandbox for finalist eligibility.

Use [the submission package](submission/README.md), [judging runbook](JUDGING.md), and [latest test report](TEST_REPORT.md). Final team details, Sandbox confirmation, and the actual external submission remain outstanding. A working demo does not itself establish compliance with those requirements.
