# Memory Court + Black Box

Memory Court finds the specific memory that caused an agent's bad decision, corrects it against verified
evidence with human sign-off, and proves the fix by rerunning the same task. Full spec: [docs/BRIEF.md](docs/BRIEF.md).

## Setup

```bash
cp .env.example .env          # fill in MONGODB_URI, LLM_*, VOYAGE_API_KEY
cd backend
uv venv --python 3.12 .venv && uv pip install -p .venv -r requirements.txt
source .venv/bin/activate
```

```bash
python scripts/flip_test.py           # Gate 0: no DB needed, LLM key needed
python scripts/setup_atlas.py --seed  # collections, validator, vector indexes, wait, seed
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173, /api proxied to :8000
```

`LLM_PROVIDER` is `anthropic` or `openai`; `LLM_MODEL` is that provider's model ID. For an
OpenAI-compatible endpoint, use `LLM_PROVIDER=openai` and set `LLM_BASE_URL` (e.g. `https://host/v1`).
The endpoint must support `tools` with `tool_choice: "required"`.

## MongoDB MCP (for inspecting data from Claude Code)

`.mcp.json` registers a project-scoped `mongodb` server via `tools/mongodb-mcp.sh`, which reads
`MONGODB_URI` from `.env`. It runs **read-only** by default; export `MDB_MCP_READ_ONLY=false` before
starting Claude Code to allow writes. Approve the server when Claude Code asks, then check with `/mcp`.

## Status

| Piece | State |
|---|---|
| config, db (indexes + validator), embeddings, llm, sim, seed, retrieval, agent, routes | written, untested against Atlas |
| `flip_test.py`, `setup_atlas.py`, `isolation_check.py` | written |
| `replay.py`, `court.py` | stubs (`NotImplementedError`) |
| frontend | Vite + React + TS + Tailwind; page skeleton on `src/mock/decision.json` |

Notes: `POST /api/demo/reset` clears documents with `delete_many` instead of dropping collections,
because dropping a collection also drops its search index. Shared prompt and tool definitions live in
`backend/app/prompts.py` (not in the brief's layout) so the live run, replay, and flip test use the same text.
