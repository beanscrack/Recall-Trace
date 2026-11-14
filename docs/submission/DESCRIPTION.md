# RecallTrace — Cerebral Valley submission description

**Event:** Agents in Context Toronto: a MongoDB Hackathon

**Track:** Memory You Can Govern

**Tagline:** Better decisions start with better memory.

## Project description

RecallTrace helps teams investigate and govern the memories behind AI agent decisions. An agent can repeatedly follow outdated advice even when its code is correct. We make that remembered context inspectable and correctable.

In our checkout simulation, an agent retrieves an old runbook and disables fraud checks. Black Box replay repeats the exact recorded decision with individual memories removed, measuring changes in structured tool selection. These comparisons identify evidence of influence, not mathematical proof of causation.

MongoDB Atlas is essential to the workflow. Voyage AI embeddings and Atlas Vector Search retrieve relevant memories with tenant, status, and expiry filtering. Atlas persists decision snapshots, replay measurements, evidence, approvals, and access logs. A reviewer checks newer verified evidence and approves a correction. One Atlas transaction quarantines the old memory and links its replacement.

Fresh retrieval then changes what the agent sees. In our validated run, the agent chose rollback instead of disabling fraud checks, and simulated fraud changed from 7.1% to 0.4%. A second tenant could neither retrieve nor directly read the first tenant’s memories.

The prototype includes a six-tab dashboard, repeated replay, human-approved versioning, 44 passing backend tests, and a verified live browser workflow. It targets incident-response and platform teams operating agents with persistent memory. Checkout outcomes are simulated, and the identity picker is a demo mechanism rather than production authentication.

## Links

- [Public GitHub repository](https://github.com/beanscrack/Recall-Trace)
- [Temporary live demo](https://hero-momentum-depot-floating.trycloudflare.com)
- [Existing one-minute video](https://hero-momentum-depot-floating.trycloudflare.com/demo.mp4) — earlier UI revision; same core workflow
- [Latest validation](../TEST_REPORT.md)

See the [submission checklist](README.md) for team details, video replacement, and eligibility checks still needed before submitting. Pairwise replay is an optional backend extension and is not part of the judge-facing demo.
