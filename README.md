# 🧠 Memory Agent

A long-term memory assistant powered by **DeepSeek V4** and **LangGraph**. It remembers the useful things you share — preferences, facts, events — and personalizes every conversation using a hybrid retrieval system that combines vector similarity, recency, and importance scoring.

---

## Features

- **Persistent Memory** — Stores durable facts, preferences, and events across sessions in SQLite + ChromaDB.
- **Smart Retrieval** — Retrieves relevant memories using a weighted blend of *vector similarity*, *recency*, and *importance*.
- **Automatic Forgetting** — Memories decay over time with a half-life of 14 days; low-importance memories expire automatically.
- **Contradiction Resolution** — When you change your mind, the LLM detects contradictions and supersedes old memories.
- **Pattern Inference** — Repeated topics (e.g., asking about Java 3+ times in a week) trigger an inferred preference memory.
- **Consolidation** — Groups of related older memories are consolidated into a single summary.
- **Multi-User** — Each user ID gets an isolated memory space. No passwords — just pick a unique ID.
- **Beautiful Web UI** — Clean, modern interface with a chat panel and a live memory panel.
- **CLI Mode** — Also works as a terminal chat via `main.py`.

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────┐
│   Web UI    │────▶│           FastAPI                 │
│ (HTML/JS)   │     │         web_app.py               │
└─────────────┘     └──────────┬───────────────────────┘
                               │
                    ┌──────────▼───────────────────────┐
                    │        LangGraph Agent            │
                    │  retrieval → agent → extraction   │
                    └──────────┬───────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
        ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
        │  ChromaDB   │ │   SQLite    │ │  DeepSeek   │
        │  (vectors)  │ │ (metadata)  │ │    LLM      │
        └─────────────┘ └─────────────┘ └─────────────┘
```

### Pipeline (per message)

1. **Retrieval** — Find top-N relevant memories via vector search, scored by similarity + recency + importance.
2. **Agent** — The LLM receives the user's message, system prompt, and any recalled memories as context.
3. **Extraction** — The LLM analyzes the turn and extracts durable facts/preferences/events as structured JSON.
4. **Forgetting** — After each turn, memories decay and low-importance ones expire. Patterns are detected and contradictions resolved.

---

## Project Structure

```
MemoryAgent/
├── main.py                  # CLI chat loop
├── web_app.py               # FastAPI web server
├── requirements.txt         # Python dependencies
├── .env                     # API key & config (create from template below)
│
├── core/
│   ├── config.py            # Environment variables & paths
│   ├── graph.py             # LangGraph agent definition
│   ├── llm.py               # DeepSeek LLM setup
│   ├── extraction.py        # Memory extraction from conversations
│   ├── retrieval.py         # Hybrid memory retrieval (vector + recency + importance)
│   ├── forgetting.py        # Decay, expiration, contradiction, consolidation
│   ├── pattern_detection.py # Inferred preferences from repeated topics
│   └── storage/
│       ├── metadata_store.py  # SQLite CRUD for memory metadata
│       └── vector_store.py    # ChromaDB vector operations
│
├── frontend/
│   ├── index.html           # Web UI
│   ├── app.js               # Frontend logic
│   └── styles.css           # Styling
│
├── tests/
│   └── test_evaluation.py   # End-to-end evaluation suite
│
└── data/                    # Auto-generated (SQLite DB + Chroma vectors)
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- A **DeepSeek API key** — get one at [platform.deepseek.com](https://platform.deepseek.com)

### 1. Clone & Install

```bash
cd MemoryAgent
pip install -r requirements.txt
```

### 2. Set Up Environment

Create a `.env` file in the project root:

```env
DEEPSEEK_API_KEY="sk-your-api-key-here"
DEEPSEEK_MODEL="deepseek-v4-flash"
```

Optional overrides:

```env
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
CHROMA_PERSIST_DIR="data/chroma"
SQLITE_DB_PATH="data/memory.db"
```

### 3. Choose Your Interface

**Web UI** (recommended):

```bash
python -m uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in your browser.

**CLI**:

```bash
python main.py
```

---

## How It Works

### Memory Lifecycle

| Stage | What Happens |
|-------|-------------|
| **Extraction** | LLM extracts facts, preferences, events, and corrections from each conversation turn. Only explicit statements are captured (no hallucinated inferences). |
| **Storage** | New memories are stored in both SQLite (metadata) and ChromaDB (embeddings). |
| **Decay** | Every memory's importance decays exponentially (half-life: 14 days). |
| **Expiration** | When importance drops below 1.0, the memory is marked as `expired`. |
| **Contradiction** | When you state something that contradicts an earlier memory, the LLM detects it and marks the old one as `superseded`. |
| **Consolidation** | Groups of 3+ related memories older than 14 days are consolidated into a summary. |
| **Pattern Inference** | If you mention a topic (e.g., "Java") 3+ times in a week, an inferred preference is created. |

### Retrieval Scoring

Relevant memories are ranked by a weighted composite score:

$S = 0.5 \times \text{similarity} + 0.2 \times \text{recency} + 0.3 \times \text{importance}$

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the web UI |
| `POST` | `/api/chat` | Send a message, get a reply + memory updates |
| `GET` | `/api/memories/{user_id}` | List memories for a user |

### Chat Request

```json
{
  "message": "I prefer Python over JavaScript",
  "user_id": "alex_01",
  "history": []
}
```

### Chat Response

```json
{
  "reply": "Got it! I'll remember you prefer Python...",
  "recalled": "User prefers Python for scripting (importance: 8.5)",
  "saved": [{"type": "preference", "content": "Prefers Python over JavaScript"}],
  "forgetting": {"expired": 1, "consolidated": []},
  "summary": {"total": 5, "high_importance": 2, "inferred": 1, "last_updated": "..."},
  "at": "2026-07-27T..."
}
```

---

## Evaluation

Run the automated evaluation suite to verify memory recall, contradiction resolution, and retrieval precision:

```bash
python tests/test_evaluation.py
```

Scenarios tested:
- **Explicit preference recall** — remembers stated language preference
- **Implicit pattern recall** — infers preference from repeated questions
- **Contradiction resolution** — supersedes old memories when corrected
- **Retrieval precision** — doesn't recall irrelevant memories

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | DeepSeek V4 (via `langchain-deepseek`) |
| Agent Framework | LangGraph |
| Vector Store | ChromaDB |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Metadata Store | SQLite |
| Web Framework | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS |

---

## License

MIT
