"""
FinDoc AI — RAG Pipeline Backend
Server: uvicorn server:app --host 127.0.0.1 --port 8000 --reload
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from rag_pipeline.config import GEMINI_API_KEY
from rag_pipeline.chroma_db import get_collection, build_vendor_lookup
from rag_pipeline.normalize import load_and_normalize
from rag_pipeline.config import CSV_PATH
from rag_pipeline.pipeline import run_pipeline

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(title="FinDoc AI — Invoice RAG Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# RAG Pipeline bootstrap
# ─────────────────────────────────────────────
print("Loading RAG pipeline components", flush=True)

collection = get_collection()
new_df, df_raw = load_and_normalize(CSV_PATH)
vendor_lookup = build_vendor_lookup(new_df)
print(f"  Collection '{collection.name}': {collection.count()} vectors", flush=True)
print(f"  Data: {len(new_df)} invoices, {len(vendor_lookup)} vendors", flush=True)

classifier = None
try:
    from rag_pipeline.models import get_classifier
    classifier = get_classifier()
    print("  Classifier loaded", flush=True)
except Exception as e:
    print(f"  Classifier skipped: {e}", flush=True)

use_gemini = False
if GEMINI_API_KEY:
    try:
        from rag_pipeline.gemini_client import get_client
        get_client()
        use_gemini = True
        print("  Gemini client ready", flush=True)
    except Exception as e:
        print(f"  Gemini skipped: {e}", flush=True)
else:
    print("  Gemini not configured (set GEMINI_API_KEY)", flush=True)

llm_pipe = None
try:
    from transformers import pipeline as hf_pipeline
    llm_pipe = hf_pipeline(
        "text-generation",
        model="HuggingFaceTB/SmolLM2-135M-Instruct",
        device="cpu",
    )
    print("  Local LLM pipeline loaded", flush=True)
except Exception as e:
    print(f"  Local LLM skipped: {e}", flush=True)

KAGGLE_FILE_DIR = CSV_PATH.parent / "batch1_1"
print(f"  File directory: {KAGGLE_FILE_DIR}", flush=True)

print("RAG pipeline ready.\n", flush=True)

# ─────────────────────────────────────────────
# Session store
# ─────────────────────────────────────────────
class Session:
    def __init__(self):
        self.created: str = datetime.utcnow().isoformat()
        self.history: list[dict] = []
        self.last_query: str = ""
        self.last_answer: str = ""
        self.last_files: list[dict] = []
        self.open_files: dict[str, str] = {}  # filename → OCR text

_sessions: dict[str, Session] = {}


def _get_session(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session()
    return _sessions[session_id]


# def _build_history_context(session: Session) -> str:
#     parts = ["--- Previous conversation ---"]
#     for msg in session.history[-6:]:
#         label = "Q" if msg["role"] == "user" else "A"
#         parts.append(f"{label}: {msg['content'][:500]}")
#     parts.append("--- End of previous conversation ---")
#     return "\n".join(parts)


def _needs_retrieval(query: str, classifier) -> bool:
    q = query.lower().strip()
    social = {"thanks", "thank", "ok", "okay", "yes", "no", "bye", "hello", "hi",
              "great", "perfect", "understood", "got it", "cool", "nice"}
    if q.split() and q.split()[0].lower().rstrip("!.,") in social and len(q.split()) <= 3:
        return False
    if classifier:
        from rag_pipeline.referee import classify_finance
        return classify_finance([query], classifier)[0]
    return True


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(default="default_user", min_length=1)
    model: str = Field(default="auto", pattern=r"^(auto|gemini|local)$")


class NewSessionResponse(BaseModel):
    session_id: str


class HealthResponse(BaseModel):
    status: str
    pipeline: str
    vectors: int
    vendors: int
    gemini_available: bool
    local_available: bool


class SessionInfoResponse(BaseModel):
    session_id: str
    created: str
    message_count: int


class OpenFileRequest(BaseModel):
    filename: str = Field(..., min_length=1)


# ─────────────────────────────────────────────
# Streaming generator
# ─────────────────────────────────────────────
async def _stream_rag_response(message: str, session_id: str, model: str = "auto") -> AsyncGenerator[str, None]:
    session = _get_session(session_id)

    use_gemini_for_request = use_gemini
    llm_pipe_for_request = llm_pipe
    if model == "gemini":
        use_gemini_for_request = True
        llm_pipe_for_request = None
    elif model == "local":
        use_gemini_for_request = False

    # ── Memory path: file chip is open, answer from OCR text ──
    if session.open_files:
        from rag_pipeline.gemini_client import ANSWER_PROMPT
        docs_text = "\n---\n".join(session.open_files.values())
        if session.last_query:
            docs_text += f"\n\n---\nPrevious context — the user asked: {session.last_query}"
        prompt = ANSWER_PROMPT.format(user_query=message, documents_text=docs_text)
        answer = None
        if use_gemini_for_request:
            try:
                from rag_pipeline.gemini_client import answer_query as gemini_answer
                answer = gemini_answer(message, list(session.open_files.values()))
            except Exception as e:
                print(f"\n[Gemini error: {e}]")
        if answer is None and llm_pipe_for_request:
            messages = [{"role": "user", "content": prompt}]
            out = llm_pipe_for_request(messages, max_new_tokens=512, temperature=0.8)
            answer = out[0]["generated_text"][-1]["content"]
            print(answer)
        if answer is None:
            answer = "No answer could be generated from the open document."
        words = answer.split(" ")
        batch = []
        for word in words:
            batch.append(word)
            if len(batch) >= 5:
                yield f"data: {' '.join(batch)}\n\n"
                batch = []
                await asyncio.sleep(0)
        if batch:
            yield f"data: {' '.join(batch)}\n\n"
        session.history.append({"role": "user", "content": message})
        session.history.append({"role": "assistant", "content": answer})
        session.last_query = message
        session.last_answer = answer
        return

    # ── Normal pipeline path ──
    # history_context = _build_history_context(session)
    # conversation_context = history_context if history_context else None

    retrieval_needed = _needs_retrieval(message, classifier)

    try:
        result = run_pipeline(
            message,
            llm_pipe=llm_pipe_for_request,
            use_gemini=use_gemini_for_request,
            # conversation_context=conversation_context,
            # needs_retrieval=retrieval_needed,
        )

        answer = result.get("answer", "No answer generated.")
        steps = result.get("steps", {})

        docs_retrieved = result.get("docs_retrieved", set())
        files_list = []
        if docs_retrieved:
            files_list = [
                {
                    "id": idx + 1,
                    "name": fname,
                    "type": "image/jpeg",
                    "url": f"/api/files/{fname}",
                }
                for idx, fname in enumerate(sorted(docs_retrieved))
            ]
            yield f"data: __files__{json.dumps(files_list)}\n\n"

        if not steps.get("passed", True):
            escaped = answer.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"
            session.history.append({"role": "user", "content": message})
            session.history.append({"role": "assistant", "content": answer})
            return

        words = answer.split(" ")
        batch = []
        for word in words:
            batch.append(word)
            if len(batch) >= 5:
                chunk = " ".join(batch)
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
                batch = []
                await asyncio.sleep(0)

        if batch:
            chunk = " ".join(batch)
            escaped = chunk.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"

        session.last_query = message
        session.last_answer = answer
        session.last_files = files_list if docs_retrieved else []
        session.history.append({"role": "user", "content": message})
        session.history.append({"role": "assistant", "content": answer})

    except Exception as exc:
        yield f"data: \u26a0\ufe0f Pipeline error: {exc}\n\n"


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        pipeline="rag_pipeline",
        vectors=collection.count(),
        vendors=len(vendor_lookup),
        gemini_available=use_gemini,
        local_available=llm_pipe is not None,
    )


@app.get("/api/files/{filename:path}")
async def get_file(filename: str):
    file_path = KAGGLE_FILE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))


@app.post("/api/session", response_model=NewSessionResponse)
async def new_session() -> NewSessionResponse:
    session_id = str(uuid.uuid4())
    _get_session(session_id)
    return NewSessionResponse(session_id=session_id)


@app.get("/api/session/{session_id}", response_model=SessionInfoResponse)
async def session_info(session_id: str) -> SessionInfoResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    return SessionInfoResponse(
        session_id=session_id,
        created=s.created,
        message_count=len(s.history),
    )


@app.delete("/api/session/{session_id}", status_code=204)
async def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


@app.post("/api/session/{session_id}/open-file")
async def open_file(session_id: str, body: OpenFileRequest) -> dict:
    session = _get_session(session_id)
    match = df_raw[df_raw["File Name"] == body.filename]
    if match.empty:
        raise HTTPException(status_code=404, detail="File not found")
    ocr_text = str(match.iloc[0].get("OCRed Text", ""))
    if not ocr_text or ocr_text in ("nan", "None", ""):
        raise HTTPException(status_code=404, detail="No OCR text for this file")
    session.open_files[body.filename] = ocr_text
    return {"status": "ok", "open_files": len(session.open_files)}


@app.post("/api/session/{session_id}/close-file")
async def close_file(session_id: str, body: OpenFileRequest) -> dict:
    session = _get_session(session_id)
    session.open_files.pop(body.filename, None)
    return {"status": "ok", "open_files": len(session.open_files)}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="message must not be blank")
    return StreamingResponse(
        _stream_rag_response(request.message.strip(), request.session_id, request.model),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


# ─────────────────────────────────────────────
# Dev entry-point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
