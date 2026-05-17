# Query Classification (`referee.py`)

## Purpose

Before doing any retrieval work, the system checks whether the user's query is actually finance-related. This prevents the pipeline from wasting compute on irrelevant questions and avoids hallucinated answers from non-financial text.

## Zero-shot classifier

**Model:** `facebook/bart-large-mnli`

Loaded once at startup via `models.get_classifier()` (HuggingFace `pipeline("zero-shot-classification", ...)`).

### `classify_finance()` (referee.py:7-21)

```python
def classify_finance(queries: list[str], classifier, threshold: float = 0.59) -> list[bool]:
    results = classifier(
        queries,
        candidate_labels=["finance", "non-finance"],
        hypothesis_template="This request is about {}.",
    )
    # If the top label is "non-finance" AND its score >= threshold → block
    # If "non-finance" but score < threshold → allow (conservative)
```

Logic:
1. If classifier is None → allow everything (defensive)
2. Classify query as "finance" or "non-finance"
3. If label is "non-finance" with score ≥ 0.59 → reject (return False)
4. If label is "non-finance" but score < 0.59 → allow (ambiguous, be conservative)
5. If label is "finance" → allow

## Integration in pipeline

In `pipeline.py:run_pipeline()`:

```python
if classifier:
    is_finance = classify_finance([user_query], classifier)[0]
    if not is_finance:
        return {"answer": "Query does not appear finance-related.", ...}
```

## Server-side social check

In `server.py:_needs_retrieval()` — an additional fast-path filter before the classifier:

```python
social = {"thanks", "thank", "ok", "okay", "yes", "no", ...}
if q.split()[0] in social and len(q.split()) <= 3:
    return False  # skip retrieval entirely
```

This catches trivial social utterances before they reach the heavier classifier.

## Server-side query classifier

In `server.py:_needs_retrieval()` — calls the same zero-shot classifier to decide if a query should trigger a retrieval or be skipped (pipeline handles the actual block via `classify_finance`).

## Related files

| File | Role |
|---|---|
| `rag_pipeline/referee.py` | `classify_finance()` function |
| `rag_pipeline/models.py` | `get_classifier()` — loads bart-large-mnli |
| `rag_pipeline/pipeline.py` | Calls `classify_finance()` at start of `run_pipeline()` |
| `backend/server.py` | `_needs_retrieval()` — social filter + classifier call |
