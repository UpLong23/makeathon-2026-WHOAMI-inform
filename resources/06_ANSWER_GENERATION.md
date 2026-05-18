# Answer Generation

Three pathways, tried in priority order:

## 1. Gemini (`gemini_client.py`)

**Condition:** `use_gemini=True` and retrieved documents exist (`ocr_docs` truthy).

```python
if use_gemini and ocr_docs:
    answer = gemini_answer(user_query, ocr_docs)
```

### `answer_query()` (gemini_client.py:50-62)

```python
def answer_query(user_query, retrieved_docs, model=GEMINI_MODEL):
    docs_text = "\n---\n".join(
        f"Document {i+1}:\n{doc[:2000]}" for i, doc in enumerate(retrieved_docs)
    )
    prompt = ANSWER_PROMPT.format(user_query=user_query, documents_text=docs_text)
    return stream_print(prompt, model=model)
```

Gemini model: `gemini-3-flash-preview` (configurable via `GEMINI_MODEL`).

### ANSWER_PROMPT

```python
"You are a financial document analyst. Answer the user's question using ONLY the provided documents."
```

## 2. Local LLM — SmolLM2-135M-Instruct

**Condition:** `llm_pipe` is available (loaded at startup) and answer is still None.

```python
if answer is None:
    if llm_pipe:
        from rag_pipeline.gemini_client import ANSWER_PROMPT
        prompt = ANSWER_PROMPT.format(user_query=user_query, documents_text=docs_text)
        messages = [{"role": "user", "content": prompt}]
        out = llm_pipe(messages, max_new_tokens=512, temperature=0.8)
        answer = out[0]["generated_text"][-1]["content"]
```

Uses the same `ANSWER_PROMPT` as Gemini, making the two pathways interchangeable from the prompt perspective.

**Model:** `HuggingFaceTB/SmolLM2-135M-Instruct` — very small (135M params), runs on CPU. Quality is limited but functional for structured invoice queries. Loaded at server startup:

```python
llm_pipe = pipeline(
    "text-generation",
    model="HuggingFaceTB/SmolLM2-135M-Instruct",
    device="cpu",
)
```

## 3. Fallback — format_answer()

**Condition:** Neither Gemini nor local LLM available.

```python
else:
    answer = format_answer(user_query, output) if output else "No documents matched your query."
```

`format_answer()` produces a structured text listing of retrieved results (see 05_RETRIEVAL.md).

## Model toggle in frontend

The user can choose which model to use via a dropdown in the chat header:

| Option | Behavior |
|---|---|
| Auto | Use Gemini if available, else local |
| Gemini | Force Gemini |
| Local | Force local SmolLM2 |

The selected model is sent as `ChatRequest.model` and mapped in `_stream_rag_response()`:

```python
if model == "gemini":
    use_gemini_for_request = True
    llm_pipe_for_request = None
elif model == "local":
    use_gemini_for_request = False
```

## Related files

| File | Role |
|---|---|
| `rag_pipeline/gemini_client.py` | Gemini streaming client, ANSWER_PROMPT |
| `rag_pipeline/pipeline.py` | LLM dispatch logic in `run_pipeline()` |
| `backend/server.py` | Model toggle, LLM loading at startup |
| `frontend/src/App.tsx` | Model dropdown in chat header |
