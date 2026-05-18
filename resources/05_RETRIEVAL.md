# Hybrid Retrieval (`pipeline.py`)

## Two-stage retrieval

ChromaDB supports rich querying with both embedding similarity and metadata filtering. The system uses both:

1. **Metadata filter** (`chroma_where`) — narrows search space using structured criteria
2. **Semantic search** (`query_texts`) — ranks results by cosine similarity

```python
query_kwargs = {
    "query_texts": [parsed["semantic_query"]],   # embedding search
    "n_results": TOP_K,                           # 5
    "include": ["documents", "metadatas", "distances"],
}
if parsed["chroma_where"]:
    query_kwargs["where"] = parsed["chroma_where"]  # metadata filter

results = collection.query(**query_kwargs)
```

## Amount post-filtering

ChromaDB metadata filters only support exact match and range operators (`$eq`, `$gte`, `$lt`), but amount parsing often produces values that don't match precisely. `post_filter_amounts()` applies an additional in-memory filter after retrieval:

```python
def post_filter_amounts(results, amount_gt, amount_lt):
    for doc_id, doc, meta, dist in zip(...):
        total = float(meta.get("total", 0))
        if amount_gt is not None and total <= amount_gt:
            continue  # exclude
        if amount_lt is not None and total >= amount_lt:
            continue  # exclude
        kept.append(...)
```

This is necessary because `amount_gt`/`amount_lt` values from the parser may not match anything in the ChromaDB metadata exactly — the in-memory pass catches edge cases.

## Document retrieval for answer generation

After retrieval, the system fetches the full OCR text for matched filenames:

```python
filenames = [m["filename"] for m in output["results"]["metadatas"][0]]
ocr_docs = df_raw[df_raw["File Name"].isin(filenames)]["OCRed Text"].tolist()
```

## Smart file filtering

`_filter_referenced_docs()` (pipeline.py:35-46) reduces the file set sent to the frontend:

```python
def _filter_referenced_docs(answer, metadatas):
    answer_lower = answer.lower()
    for meta in metadatas:
        for field in ["invoice_number", "vendor", "doc_id"]:
            if str(meta.get(field, "")).lower() in answer_lower:
                referenced.add(meta["filename"])
    return referenced
```

Only invoices whose invoice_number, vendor, or doc_id appear in the answer text are sent. This prevents showing 5 file chips when only 1 invoice was actually discussed.

## format_answer() fallback

When no LLM is available (no Gemini key, no local pipeline), `format_answer()` generates a structured text response:

```python
def format_answer(user_query, output):
    for rank, (doc_id, doc, meta, dist) in enumerate(...):
        lines.append(f"  Result #{rank}  (cosine distance: {dist:.4f})")
        lines.append(f"  Vendor: {meta.get('vendor')}")
        lines.append(f"  Invoice #: {meta.get('invoice_number')}")
        ...
```

## Related files

| File | Role |
|---|---|
| `rag_pipeline/pipeline.py` | `hybrid_retrieve()`, `post_filter_amounts()`, `format_answer()`, `_filter_referenced_docs()` |
| `rag_pipeline/query_parser.py` | Produces `chroma_where` and `semantic_query` used in retrieval |
| `rag_pipeline/chroma_db.py` | Collection setup with cosine distance |
