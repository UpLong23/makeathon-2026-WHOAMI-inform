"""
FinDoc AI — Receipt Agent Backend
Model : HuggingFaceTB/SmolLM2-135M-Instruct
Server: uvicorn main:app --host 127.0.0.1 --port 8000 --reload
"""

import asyncio
import json
import uuid
from collections import deque
from datetime import datetime
from threading import Thread
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(title="FinDoc AI — Receipt Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Model bootstrap
# ─────────────────────────────────────────────
MODEL_NAME = "HuggingFaceTB/SmolLM2-135M-Instruct"

print(f"Loading '{MODEL_NAME}'…")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
print("Model ready.")

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are FinDoc, a precise and friendly receipt & expense assistant.

Your capabilities:
- Parse receipt data (items, prices, quantities, dates, vendors)
- Calculate totals, subtotals, taxes, tips, and discounts
- Split bills between people (equal or custom splits)
- Track multiple receipts across a session and compare them
- Detect duplicate charges or anomalies
- Summarize expenses by category (food, transport, utilities, etc.)
- Convert currencies when asked

Rules:
- Always show your math step by step when calculating
- Format monetary values consistently (e.g. €12.50 or $12.50)
- If the user pastes raw receipt text, extract all line items into a clean table
- Remember every receipt and expense mentioned in this conversation
- If asked "what have I spent so far?", total everything from the session
- Be concise. No filler. Numbers first, explanation second.
"""

# ─────────────────────────────────────────────
# Session store
# ─────────────────────────────────────────────
MAX_PAIRS = 12
MAX_RECEIPTS = 50

# How many tokens to accumulate before flushing a chunk to the client.
# Larger = fewer round-trips, smoother rendering; too large = choppy start.
TOKEN_BATCH_SIZE = 1


class Session:
    def __init__(self):
        self.history: deque = deque(maxlen=MAX_PAIRS * 2)
        self.receipts: list[dict] = []
        self.summary: str = ""
        self.created: str = datetime.utcnow().isoformat()
        self.total_spent: float = 0.0

    def add_receipt(self, receipt: dict) -> None:
        self.receipts.append(receipt)
        self.total_spent += receipt.get("total", 0.0)

    def session_context(self) -> str:
        parts: list[str] = []
        if self.summary:
            parts.append(f"[EARLIER IN THIS SESSION]\n{self.summary}")
        if self.receipts:
            lines = [f"[RECEIPTS TRACKED THIS SESSION — running total: {self.total_spent:.2f}]"]
            for i, r in enumerate(self.receipts, 1):
                vendor = r.get("vendor", "Unknown")
                date   = r.get("date", "")
                total  = r.get("total", 0.0)
                lines.append(f"  {i}. {vendor}{' (' + date + ')' if date else ''} — {total:.2f}")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)


_sessions: dict[str, Session] = {}


def _get_session(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session()
    return _sessions[session_id]


def _build_messages(session: Session, user_message: str) -> list[dict]:
    ctx = session.session_context()
    system_content = SYSTEM_PROMPT
    if ctx:
        system_content += f"\n\n{ctx}"
    messages = [{"role": "system", "content": system_content}]
    messages += list(session.history)
    messages.append({"role": "user", "content": user_message})
    return messages


def _maybe_compress(session: Session) -> None:
    if len(session.history) < MAX_PAIRS * 2:
        return
    temp = list(session.history)
    oldest = []
    for msg in temp[:4]:
        role = "User" if msg["role"] == "user" else "Assistant"
        oldest.append(f"{role}: {msg['content'][:300]}")
    snippet = "\n".join(oldest)
    if session.summary:
        session.summary += "\n" + snippet
    else:
        session.summary = snippet
    if len(session.summary) > 1200:
        session.summary = "…" + session.summary[-1200:]


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(default="default_user", min_length=1)


class AddReceiptRequest(BaseModel):
    session_id: str
    vendor: str = ""
    date: str = ""
    total: float = 0.0
    items: list[dict] = []


class NewSessionResponse(BaseModel):
    session_id: str


class HealthResponse(BaseModel):
    status: str
    model: str


class SessionInfoResponse(BaseModel):
    session_id: str
    created: str
    message_count: int
    receipt_count: int
    total_spent: float
    has_summary: bool


# ─────────────────────────────────────────────
# Streaming generator  ← key changes here
# ─────────────────────────────────────────────
async def _stream_response(message: str, session_id: str) -> AsyncGenerator[str, None]:
    session = _get_session(session_id)

    try:
        _maybe_compress(session)
        messages = _build_messages(session, message)

        input_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer([input_text], return_tensors="pt")

        streamer = TextIteratorStreamer(
            tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=400,
            temperature=0.3,
            do_sample=True,
            repetition_penalty=1.1,
        )

        thread = Thread(target=model.generate, kwargs=generation_kwargs, daemon=True)
        thread.start()

        full_response: list[str] = []
        batch: list[str] = []

        for token in streamer:
            if not token:
                continue

            full_response.append(token)
            batch.append(token)

            # Flush every TOKEN_BATCH_SIZE tokens so the client receives
            # small, frequent chunks instead of one-token-per-frame.
            if len(batch) >= TOKEN_BATCH_SIZE:
                chunk = "".join(batch)
                batch = []
                # Escape newlines so a single SSE "data:" line carries the chunk.
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
                # Yield control to the event loop without a sleep penalty.
                await asyncio.sleep(0)

        # Flush any remaining tokens
        if batch:
            chunk = "".join(batch)
            escaped = chunk.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"
            await asyncio.sleep(0)

        reply = "".join(full_response).strip()
        if reply:
            session.history.append({"role": "user",      "content": message})
            session.history.append({"role": "assistant", "content": reply})

    except Exception as exc:
        yield f"data: ⚠️ Generation error: {exc}\n\n"


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL_NAME)


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
        receipt_count=len(s.receipts),
        total_spent=s.total_spent,
        has_summary=bool(s.summary),
    )


@app.delete("/api/session/{session_id}", status_code=204)
async def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


@app.post("/api/session/{session_id}/receipt", status_code=201)
async def add_receipt(session_id: str, body: AddReceiptRequest) -> dict:
    session = _get_session(session_id)
    receipt = {
        "vendor": body.vendor,
        "date":   body.date,
        "total":  body.total,
        "items":  body.items,
    }
    session.add_receipt(receipt)
    return {"receipt_count": len(session.receipts), "total_spent": session.total_spent}


@app.get("/api/session/{session_id}/receipts")
async def get_receipts(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    return {
        "receipts":    s.receipts,
        "total_spent": s.total_spent,
        "count":       len(s.receipts),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="message must not be blank")
    return StreamingResponse(
        _stream_response(request.message.strip(), request.session_id),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control":     "no-cache",
        },
    )


# ─────────────────────────────────────────────
# Dev entry-point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)