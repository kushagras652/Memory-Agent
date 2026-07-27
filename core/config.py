import os
from pathlib import Path
import sys

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT=Path(__file__).resolve().parent.parent

DEEPSEEK_API_KEY=os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL=os.environ.get("DEEPSEEK_MODEL","deepseek-v4-flash")

EMBEDDING_MODEL=os.environ.get(
    "EMBEDDING_MODEL","sentence-transformers/all-MiniLM-L6-v2"
)

def _resolve(env_var:str,default:str)->str:
    raw=os.environ.get(env_var,default)
    return str((PROJECT_ROOT/raw).resolve())


CHROMA_PERSIST_DIR=_resolve("CHROMA_PERSIST_DIR","data/chroma")
SQLITE_DB_PATH=_resolve("SQLITE_DB_PATH","data/memory.db")
LAST_USER_FILE=_resolve("LAST_USER_FILE","data/.last_user_id")


def require_api_key() -> None:
    """Validate that DEEPSEEK_API_KEY is set; exit with a helpful message if not."""
    if not DEEPSEEK_API_KEY:
        print(
            "Missing DEEPSEEK_API_KEY.\n"
            " 1. cp .env.example .env (if you haven't already)\n"
            " 2. edit .env and set DEEPSEEK_API_KEY=YOUR_REAL_API_KEY",
            file=sys.stderr,
        )
        sys.exit(1)