# RecallTrace

**Trace the memory. Review the evidence. Change the next decision.**

RecallTrace helps teams debug and govern persistent AI memory. In a simulated checkout incident, an agent follows an outdated runbook and disables fraud checks. Black Box replays the exact recorded decision with individual memories removed, measuring action changes across repeated trials. It provides evidence of memory influence without claiming causal proof.

MongoDB Atlas stores versioned memories, evidence, decision snapshots, replays, approvals, and access logs. Atlas Vector Search retrieves semantically relevant memories with tenant, active-status, and expiry filters. Voyage supplies embeddings, and Nemotron 3.5 Super VL supplies structured tool calls through OpenRouter.

A named reviewer approves a correction against newer verified evidence for the same service. One Atlas transaction quarantines the old memory and links its replacement. Fresh retrieval changes the agent's action from disabling fraud checks to rolling back the deployment. A second tenant cannot retrieve or directly read the first tenant's memories.

## Links and materials

- Public source: https://github.com/beanscrack/Recall-Trace
- Temporary live app and video: [deployment details](../DEPLOYMENT.md)
- Actual run IDs and measured results: [validated-run.json](validated-run.json)
- Tests and limits: [validation report](../VALIDATION.md)

The one-minute video contains actual browser captures and source-code excerpts, with generated narration. A complete raw browser recording is retained locally. This is a simulated checkout system with a session picker, not real authentication or production payments.

## Deferred final submission details

The user explicitly deferred the team name, member list, Cerebral Valley submission URL/account, and confirmation that the Atlas cluster was created through the event Sandbox invitation. Do not invent those details or claim finalist eligibility from a successful database connection alone. No competition submission has been made.
