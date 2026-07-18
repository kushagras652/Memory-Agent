import os
from pathlib import Path

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
