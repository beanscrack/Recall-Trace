"""Environment loading. Reads the repo-root .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "memory_court")
# Optional process-local override for environments whose DNS omits Atlas SRV records.
MONGODB_DNS_NAMESERVERS = [s.strip() for s in os.getenv("MONGODB_DNS_NAMESERVERS", "").split(",") if s.strip()]
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "") or None  # OpenAI-compatible endpoint
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

# Session user -> tenant. The client never sends a tenant.
USERS = {
    "sre-oncall": "acme-pay",
    "reviewer-dana": "acme-pay",
    "platform-lee": "globex",
}
