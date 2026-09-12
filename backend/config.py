import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)
 
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
if LLM_PROVIDER not in {"mock", "luna"}:
    raise ValueError("LLM_PROVIDER must be mock or luna")

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

