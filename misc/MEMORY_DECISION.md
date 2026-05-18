# Memory & Retrieval Decision

## Approach

Conversation memory is **always kept** (last 6 messages). The zero-shot classifier (`facebook/bart-large-mnli`) decides whether a query needs document retrieval or can be answered from memory alone. The classification strategy depends on whether there's prior conversation:

- **No history** → `["finance", "non-finance"]` — blocks irrelevant queries
- **Has history** → `["search_documents", "continue_conversation"]` — prevents follow-ups ("that invoice", "tell me more") from re-triggering retrieval

## Flow

| Query type | History? | Retrieval? | Behavior |
|---|---|---|---|
| Finance query | No | Yes | Full RAG, files shown |
| Finance query | Yes | Depends | Classifier decides search_documents vs continue_conversation |
| Social ("thanks") | Yes | No | LLM answers from memory only |
| Non-finance first query | No | No | Returns "No documents matched" |
| Follow-up ("that invoice", "tell me more") | Yes | No | Classified as continue_conversation, answered from memory |
| Fresh finance query (after chat) | Yes | Yes | Classified as search_documents, RAG + memory context |

## Key changes

### `backend/server.py`
- Removed `FOLLOWUP_INDICATORS` and `_is_followup()` heuristic
- Added `_build_history_context()` — formats last 6 messages as `--- Previous conversation ---` / `Q:...` / `A:...` / `--- End of previous conversation ---`
- Added `_needs_retrieval()` — social short queries skip immediately; otherwise uses the classifier with labels `["finance", "non-finance"]` (no history) or `["search_documents", "continue_conversation"]` (has history)
- `_stream_rag_response` always builds history context, passes `needs_retrieval` to pipeline

### `rag_pipeline/pipeline.py`
- Removed `classifier` parameter from `run_pipeline()` — server now owns classification
- Removed the "not finance" early return (moved to server's `_needs_retrieval`)
- Referee (`needs_referee`) only fires when `needs_retrieval=True`

### `rag_pipeline/referee.py`
- `classify_finance()` unchanged — used by server via `_needs_retrieval`

## Quirks

- Social-only queries ("thanks", "ok") correctly skip retrieval but the tiny 135M model still generates a finance-style answer from memory rather than a polite response — a model quality limitation, not a logic bug.
