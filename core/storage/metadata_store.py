import sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
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
 last_decayed_at TEXT NOT NULL,
 access_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);


CREATE TABLE IF NOT EXISTS interaction_tags(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id TEXT NOT NULL,
topic TEXT NOT NULL,
created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tags_user_topic ON interaction_tags(user_id,topic);
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

        cols=[r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()]
        if "source" not in cols:
            conn.execute(
                "ALTER TABLE memories ADD COLUMN source TEXT NOT NULL DEFAULT 'explicit'"
            )
        if "last_decayed_at" not in cols:
            conn.execute(
                f"ALTER TABLE memories ADD COLUMN last_decayed_at TEXT NOT NULL DEFAULT '{_now()}'"
            )

def insert_memory(memory_id:str,user_id:str,type_:str,content:str,importance:float,source:str ="explicit")->None:
    now=_now()
    with get_connection() as conn:
        conn.execute(
            """
        INSERT INTO memories
        (id,user_id,type,content,importance,source,status,created_at,last_accessed,last_decayed_at,access_count)
        VALUES (?,?,?,?,?,?,'active',?,?,?,0)
        """,
        (memory_id,user_id,type_,content,importance,source,now,now,now)
        )

def get_memory(memory_id:str)->Optional[sqlite3.Row]:
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



def update_importance(memory_id:str,importance:float,decayed_at:str)->None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE memories SET importance=?,last_decayed_at=? WHERE id=?",
            (importance,decayed_at,memory_id)
        )


def delete_old_tags(retention_days:int)->int:
    cutoff=(datetime.now(timezone.utc)- timedelta(days=retention_days)).isoformat()
    with get_connection() as conn:
        cursor=conn.execute(
            "DELETE FROM interaction_tags WHERE created_at < ?",(cutoff,)
        )
        return cursor.rowcount

def log_topics(user_id:str,topics:list[str])->None:
    if not topics :
        return
    
    now=_now()
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO interaction_tags (user_id,topic,created_at) VALUES (?,?,?)",
            [(user_id,t.strip().lower(),now) for t in topics if t.strip()],
        )


def get_recent_topic_count(user_id:str,window_days:int)->dict[str,int]:
    cutoff=(datetime.now(timezone.utc)- timedelta(days=window_days)).isoformat()
    with get_connection() as conn:
        rows=conn.execute(
            """
            SELECT topic,COUNT(*) as cnt FROM interaction_tags 
            WHERE user_id=? AND created_at >= ?
            GROUP BY topic
            """,
            (user_id,cutoff),
        ).fetchall()
        return {row['topic']: row['cnt'] for row in rows}
