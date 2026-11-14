#!/usr/bin/env bash
# Starts the MongoDB MCP server with MONGODB_URI from the repo's .env (never committed).
# Read-only by default: the MCP is for inspecting data; the app writes through pymongo.
# Set MDB_MCP_READ_ONLY=false in your shell to allow writes from Claude Code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
if [ -z "${MONGODB_URI:-}" ]; then echo "mongodb-mcp: MONGODB_URI missing from $ROOT/.env" >&2; exit 1; fi
export MDB_MCP_CONNECTION_STRING="$MONGODB_URI"
export MDB_MCP_READ_ONLY="${MDB_MCP_READ_ONLY:-true}"
export MDB_MCP_TELEMETRY="${MDB_MCP_TELEMETRY:-disabled}"
exec npx -y mongodb-mcp-server@3.3.0
