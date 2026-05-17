# Query Parser (`query_parser.py`)

## Purpose

Converts a natural-language finance query into structured ChromaDB metadata filters and a semantic search string. This is the bridge between "Find invoices from Nguyen-Roach in February 2021 over $500" and `{"$and": [{"vendor_normalized": {"$eq": "nguyen-roach"}}, {"invoice_date_int": {"$gte": 20210201}}, {"invoice_date_int": {"$lt": 20210301}}]}`.

## Parser output schema

```python
{
    "intent": "search_documents",
    "semantic_query": "Find invoices over 500",   # leftover terms for embedding search
    "chroma_where": {"$and": [... filters ...]},    # metadata filter for ChromaDB
    "source_column": "line_items" | "rawtext" | None,
    "amount_gt": 500.0,     # optional
    "amount_lt": None,      # optional
}
```

## Extraction rules (in order)

### doc_type
- `"invoice"` → `{"doc_type": {"$eq": "invoice"}}`
- `"receipt"` → `{"doc_type": {"$eq": "receipt"}}`

### source_column
- `"line items"`, `"items"` → search in itemized descriptions only
- `"raw text"`, `"description"` → search in raw text only

### vendor
- Matches against `vendor_lookup` dict (sorted by key length descending for greedy matching)
- `"Nguyen-Roach"` → `{"vendor_normalized": {"$eq": "nguyen-roach"}}`

### invoice_number
- Regex `\b\d{6,10}\b` for numeric invoice numbers

### currency
- `$`, `usd`, `dollar` → `{"currency": {"$eq": "USD"}}`
- `€`, `eur`, `euro` → `{"currency": {"$eq": "EUR"}}`

### status
- `"paid"` → `{"status": {"$eq": "paid"}}`
- `"unpaid"/"outstanding"/"overdue"` → `{"status": {"$in": ["unpaid", "outstanding", "overdue"]}}`

### date ranges (multiple formats)

| Pattern | Example | ChromaDB filter |
|---|---|---|
| `"February 2021"` | `"february 2021"` | `{"$gte": 20210201, "$lt": 20210301}` |
| `"in 2021"` | `"in 2021"` | `{"$gte": 20210101, "$lt": 20220101}` |
| `"Q1 2021"` | `"q1 2021"` | `{"$gte": 20210101, "$lt": 20210401}` |
| `"first quarter 2021"` | | Same as Q1 |

Date filters use `invoice_date_int` — an integer in YYYYMMDD format stored in metadata.

### amount thresholds
- `"over 500"`, `"greater than 500"`, `"above $500"` → `amount_gt = 500.0`
- `"under 100"`, `"less than 100"`, `"below $100"` → `amount_lt = 100.0`

## Filter combination

When multiple filters match, they're combined with `$and`:
```python
if len(filters) == 1:
    chroma_where = filters[0]
elif len(filters) > 1:
    chroma_where = {"$and": filters}
```

## Semantic query construction

The `semantic_query` is the original query with all recognized keywords removed (stopwords, month names, filter keywords, digits). This clean semantic text is used for embedding similarity search in ChromaDB.

```python
semantic_terms = [t for t in tokens if t not in ignored and not t.isdigit() and len(t) > 1]
semantic_query = " ".join(semantic_terms) or query  # fallback to original
```

## Related files

| File | Role |
|---|---|
| `rag_pipeline/query_parser.py` | Full parser implementation |
| `rag_pipeline/pipeline.py` | `hybrid_retrieve()` calls `parse_user_query()` |
| `rag_pipeline/referee.py` | `needs_referee()` checks parser output quality |
