"""Browser interface for the Memory Agent.

Run with: uvicorn web_app:app --reload
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from core.forgetting import run_forgetting_job
from core.graph import SYSTEM_PROMPT, build_graph
from core.storage import metadata_store


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Memory Agent")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "frontend"), name="assets")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    user_id: str = Field(min_length=1, max_length=100)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


def _as_dict(row) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "content": row["content"],
        "importance": round(row["importance"], 1),
        "source": row["source"],
        "status": row["status"],
        "created_at": row["created_at"],
        "access_count": row["access_count"],
    }


def _memory_summary(user_id: str) -> dict:
    memories = metadata_store.list_memories(user_id)
    return {
        "total": len(memories),
        "high_importance": sum(item["importance"] >= 7 for item in memories),
        "inferred": sum(item["source"] == "inferred" for item in memories),
        "last_updated": max((item["created_at"] for item in memories), default=None),
    }


@app.on_event("startup")
def initialize_storage() -> None:
    metadata_store.init_db()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "frontend" / "index.html")


@app.get("/api/memories/{user_id}")
def memories(user_id: str, status: Literal["active", "expired", "superseded"] = "active") -> dict:
    return {
        "memories": [_as_dict(row) for row in metadata_store.list_memories(user_id, status)],
        "summary": _memory_summary(user_id),
    }


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    try:
        graph = build_graph()
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for item in payload.history:
            content = item.get("content", "").strip()
            if not content:
                continue
            messages.append(HumanMessage(content=content) if item.get("role") == "user" else AIMessage(content=content))
        messages.append(HumanMessage(content=payload.message.strip()))
        result = graph.invoke({"messages": messages, "user_id": payload.user_id.strip()})
        forgetting = run_forgetting_job(payload.user_id.strip())
        return {
            "reply": result["messages"][-1].content,
            "recalled": result.get("retrieved_context", ""),
            "saved": result.get("last_extracted", []),
            "forgetting": forgetting,
            "summary": _memory_summary(payload.user_id.strip()),
            "at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
