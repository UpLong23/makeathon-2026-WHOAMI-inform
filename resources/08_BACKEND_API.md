# Backend API (`server.py`)

## FastAPI server

**Framework:** FastAPI with Uvicorn
**Port:** 8000
**CORS:** All origins allowed (development)

## Startup bootstrap

At import time, the server loads all RAG components:

```python
collection = get_collection()                        # ChromaDB
new_df, df_raw = load_and_normalize(CSV_PATH)        # Invoice data
vendor_lookup = build_vendor_lookup(new_df)           # Vendor name mapping
classifier = get_classifier()                         # bart-large-mnli
use_gemini = bool(GEMINI_API_KEY)                     # Gemini toggle
llm_pipe = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-135M-Instruct")  # local LLM
```

All models live in memory for the lifetime of the server process.

## Session management

Simple in-memory dict keyed by `session_id`:

```python
class Session:
    def __init__(self):
        self.history: list[dict] = []           # {role, content} pairs
        self.last_query: str = ""
        self.last_answer: str = ""
        self.last_files: list[dict] = []
```

Sessions are used to track conversation history (though memory-based retrieval is currently disabled).

## API endpoints

### `POST /api/chat`

Main streaming endpoint. Accepts:

```json
{
    "message": "Find invoices from Nguyen-Roach",
    "session_id": "default_user",
    "model": "auto"     // "auto" | "gemini" | "local"
}
```

Returns `text/event-stream` with SSE events:

**File metadata event:**
```
data: __files__[{"id": 1, "name": "batch1-0494.jpg", "type": "image/jpeg", "url": "/api/files/batch1-0494.jpg"}]
```

**Answer chunks (5 words each):**
```
data: Here are the invoices found
data: in the provided documents.
```

**Error:**
```
data: ⚠️ Pipeline error: ...
```

### `GET /api/health`

Returns pipeline status:

```json
{
    "status": "ok",
    "pipeline": "rag_pipeline",
    "vectors": 998,
    "vendors": 493,
    "gemini_available": true,
    "local_available": true
}
```

### `GET /api/files/{filename}`

Serves invoice JPEG images from the Kaggle dataset directory:

```python
KAGGLE_FILE_DIR = CSV_PATH.parent / "batch1_1"  # ~/.cache/kagglehub/.../batch1_1/
file_path = KAGGLE_FILE_DIR / filename
return FileResponse(str(file_path))
```

### `POST /api/session`
Creates a new session and returns its UUID.

### `GET /api/session/{session_id}`
Returns session metadata (created, message_count).

### `DELETE /api/session/{session_id}`
Clears a session from memory.

## SSE streaming implementation

`_stream_rag_response()` is an async generator:

1. Checks model selection (auto → use Gemini if available)
2. Social/finance classifier check (`_needs_retrieval()`)
3. Calls `run_pipeline()` — blocks until complete
4. Yields `__files__` event if documents were retrieved
5. Yields answer words in 5-word batches via SSE
6. Stores turn in session history

## Run command

```bash
# With reload (development):
python backend/server.py

# Manually:
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

## Related files

| File | Role |
|---|---|
| `backend/server.py` | FastAPI app, endpoints, SSE streaming |
| `rag_pipeline/pipeline.py` | `run_pipeline()` called by server |
| `rag_pipeline/gemini_client.py` | Gemini client loaded at startup |
