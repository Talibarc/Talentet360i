import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)
 
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
if LLM_PROVIDER not in {"mock", "luna"}:
    raise ValueError("LLM_PROVIDER must be mock or luna")


def _optional_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


_demo_identities_override = _optional_bool("DEMO_IDENTITIES_ENABLED")
DEMO_IDENTITIES_ENABLED = (
    LLM_PROVIDER == "mock" if _demo_identities_override is None else _demo_identities_override
)

# Preserve the existing CIS adapter and legacy environment compatibility.
# A supplied LUNA value takes precedence over its legacy CIS counterpart.
CIS_API_KEY = os.getenv("LUNA_API_KEY") or os.getenv("CIS_API_KEY", "")
CIS_BASE_URL = os.getenv("LUNA_BASE_URL") or os.getenv("CIS_BASE_URL", "")
CIS_MODEL = os.getenv("LUNA_MODEL") or os.getenv("CIS_MODEL", "hack-fest-gpt-5.6-luna")
CIS_API_VERSION = (
    os.getenv("LUNA_API_VERSION") or os.getenv("CIS_API_VERSION", "2025-03-01-preview")
)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or (
    f"sqlite:///{(ENV_FILE.parent / 'talent360i.db').as_posix()}"
)

RAG_SOURCE_DIR = Path(os.getenv("RAG_SOURCE_DIR", ENV_FILE.parent / "tests" / "fixtures" / "synthetic_rag"))
RAG_INDEX_DIR = Path(os.getenv("RAG_INDEX_DIR", ENV_FILE.parent / ".rag_index"))
ALLOW_SYNTHETIC_RAG = os.getenv("ALLOW_SYNTHETIC_RAG", "false").strip().lower() in {"1", "true", "yes"}
RAG_MAX_FILE_BYTES = int(os.getenv("RAG_MAX_FILE_BYTES", str(25 * 1024 * 1024)))
RAG_MAX_BATCH_FILES = int(os.getenv("RAG_MAX_BATCH_FILES", "20"))
RAG_MAX_BATCH_BYTES = int(os.getenv("RAG_MAX_BATCH_BYTES", str(100 * 1024 * 1024)))

