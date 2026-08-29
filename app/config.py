import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
JUDGE_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
POLICIES_DIR = DATA_DIR / "policies"
SOURCE_DOCS_DIR = DATA_DIR / "source_docs"
DB_PATH = PROJECT_ROOT / "audit.db"

SEVERITY_MAP = {"none": 0.0, "low": 0.3, "medium": 0.6, "high": 1.0}
