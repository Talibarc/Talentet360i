import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)
 
CIS_API_KEY = os.getenv("CIS_API_KEY", "")
CIS_BASE_URL = os.getenv("CIS_BASE_URL", "")
CIS_MODEL = os.getenv("CIS_MODEL", "hack-fest-gpt-5.6-luna")
CIS_API_VERSION = os.getenv("CIS_API_VERSION", "2025-03-01-preview")
 