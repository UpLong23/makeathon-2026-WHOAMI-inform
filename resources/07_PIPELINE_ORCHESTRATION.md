# Pipeline Orchestration (`pipeline.py`)

## `run_pipeline()` — end-to-end flow

This is the central orchestrator. Called by both the CLI (`query.py`) and the web backend (`server.py`).

```python
def run_pipeline(
    user_query: str,
    collection=None, vendor_lookup=None, df_raw=None,  # data
    llm_pipe=None,     # local LLM
    use_gemini=False,  # Gemini toggle
    n_results=TOP_K,   # default 5
) -> dict:
```

### Step-by-step execution

```
1. _ensure_data()          Load/cache collection, vendor_lookup, df_raw
2. _ensure_classifier()    Load/cache bart-large-mnli classifier
3. classify_finance()      Reject non-finance queries early
4. parse_user_query()      NL → structured filters + semantic query
5. needs_referee()?        If parser output uncertain → LLM corrects it
6. hybrid_retrieve()       ChromaDB query (embedding + metadata filters)
7. post_filter_amounts()   In-memory amount filtering
8. _filter_referenced_docs()  Answer text → relevant file subset
9. Answer generation:      Gemini → local LLM → format_answer fallback
10. Return dict
```

### Return value

```python
{
    "steps": step_classify,       # {"passed": bool, "message": str}
    "parse": step_parse,          # {"passed": True, "parsed": dict}
    "referee": step_referee,      # {"called": bool, "result": dict | None}
    "retrieve": step_retrieve,    # {"passed": True, "n_results": int}
    "answer": str,                # Generated answer text
    "docs_retrieved": set,        # Filtered filename set for frontend
}
```

### Caching

`_ensure_data()` and `_ensure_classifier()` use a module-level `_cache` dict to avoid reloading models on every call:

```python
_cache = {}

def _ensure_data():
    if "collection" not in _cache:
        _cache["collection"] = get_collection()
        ...
    return _cache["collection"], _cache["vendor_lookup"], _cache["df_raw"]
```

## CLI entry points

| Command | Purpose |
|---|---|
| `python -m rag_pipeline.query "..."` | Single query, output to stdout |
| `python -m rag_pipeline.query -i` | Interactive REPL |
| `python -m rag_pipeline.query "..." --stream` | Query + Gemini answer |
| `python -m rag_pipeline.query "..." --parse-only` | Show parsed query only |
| `python -m rag_pipeline.serve` | Pre-load all models + interactive shell |
| `python -m rag_pipeline.demo` | Full-pipeline demo with Gemini |

## Related files

| File | Role |
|---|---|
| `rag_pipeline/pipeline.py` | `run_pipeline()` + helper functions |
| `rag_pipeline/query.py` | CLI query tool |
| `rag_pipeline/serve.py` | Interactive REPL |
| `rag_pipeline/demo.py` | Full-pipeline demo |
| `backend/server.py` | Web server that calls `run_pipeline()` |
