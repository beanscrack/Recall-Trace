# RecallTrace

Hackathon project; spec is docs/BRIEF.md (read sections 2, 6, 8 before changing behaviour).
- Three people commit here: small commits, don't reformat files you weren't asked to change.
- Data model in BRIEF section 6 is the contract between workstreams.
- `retrieval.search_memories` is the only path the agent uses to read memories; tenant comes from the session.
- `llm.decide` must stay pure (no DB). Never print or commit keys; `.env` is gitignored.
- Backend commands run from `backend/` with `.venv` active. MCP `mongodb` server is read-only by default.
