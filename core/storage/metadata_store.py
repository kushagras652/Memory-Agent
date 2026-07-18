import sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from typing import Optional

from core.config import SQLITE_DB_PATH

SCHEMA="""
CREATE TABLE IF NOT EXISTS memories(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL,
 type TEXT NOT NULL,
 content TEXT NOT NULL,
 importance REAL NOT NULL,
 status TEXT NOT NULL DEFAULT 'active',
 created_at TEXT NOT NULL,
 last_accessed TEXT NOT NULL,
 access_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
"""


def _now()->str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    Path(SQLITE_DB_PATH).parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory=sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)

def insert_memory(memory_id:str,user_id:str,type_:str,content:str,importance:float,)->None:
    now=_now()
    with get_connection() as conn:
        conn.execute(
            """
        INSERT INTO memories
        (id,user_id,type,content,importance,status,created_at,last_accessed,access_count)
        VALUES (?,?,?,?,?,'active',?,?,0)
        """,
        (memory_id,user_id,type_,content,importance,now,now)
        )

def get_memory(memory_id:str)->None:
    with get_connection() as conn:
        row=conn.execute(
            "SELECT * FROM memories WHERE id=?",(memory_id,)
        ).fetchone()
        return row
    
def touch_memory(memory_id:str)->None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE memories
            SET access_count=access_count+1,last_accessed=?
            WHERE id=?
            """,
            (_now(),memory_id),
        )
        
def list_memories(user_id:str,status:str='active')->list[sqlite3.Row]:
    with get_connection() as conn:
        rows=conn.execute(
            "SELECT * FROM memories WHERE user_id=? AND status = ? ORDER BY created_at DESC",
            (user_id,status),
        ).fetchall()
        return rows
    
def set_status(memory_id:str,status:str)->None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE memories SET status = ? WHERE id = ?",(status,memory_id)
        )
