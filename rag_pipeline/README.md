# rag_pipeline

Modular Python port of `rag.ipynb` — a finance-document RAG pipeline using ChromaDB, Sentence Transformers, and optional Gemini/HuggingFace validation.

## Files

| File | Purpose |
|---|---|
| `config.py` | Paths, model names, API keys (from env), hyperparameters |
| `models.py` | Singleton `FinLangEmbeddingFunction` + HF classifier loader |
| `normalize.py` | `normalize_invoice()` — raw OCR JSON → structured dict. `load_and_normalize()` — CSV → DataFrames |
| `chroma_db.py` | `get_collection()`, `delete_collection()`, `build_vendor_lookup()` |
| `ingestion.py` | `build_records()` — create text chunks with metadata. `ingest_data()` — upsert into ChromaDB |
| `query_parser.py` | `parse_user_query()` — rule-based query parser returning `chroma_where` filters |
| `pipeline.py` | `hybrid_retrieve()`, `post_filter_amounts()`, `format_answer()`, `run_pipeline()` — full chain |
| `referee.py` | `classify_finance()`, `needs_referee()` heuristics, `REFEREE_PROMPT`, `call_referee_llm()` |
| `gemini_client.py` | Gemini client singleton, `stream_print()`, `answer_query()` |
| `ingest.py` | CLI to ingest data into ChromaDB |
| `query.py` | CLI to query the RAG system |
| `serve.py` | Pre-loads all models + data, drops into interactive Python shell |
| `demo.py` | Interactive CLI: type a query → parse → retrieve → Gemini streams answer |

## Usage

All commands run from `.data/`:

### 1. Ingest data

```bash
# First-time ingestion (creates collection)
python -m rag_pipeline.ingest

# Re-ingest from scratch (drops collection first)
python -m rag_pipeline.ingest --recreate

# Custom CSV
python -m rag_pipeline.ingest --csv /path/to/data.csv
```

### 2. Query

```bash
# One-shot query (auto-loads everything, slow on first call)
python -m rag_pipeline.query "Find Nguyen-Roach from February 2021"

# Show parsed query only (no retrieval)
python -m rag_pipeline.query "invoices over $500" --parse-only

# Stream an answer from Gemini
GEMINI_API_KEY=xxx python -m rag_pipeline.query "Which vendor has the highest total?" --stream

# Interactive REPL (loads everything once)
python -m rag_pipeline.query -i
```

### 3. Serve — warm-start interactive shell

Pre-loads **all** models (embedding, classifier, Gemini client), ChromaDB collection, and invoice data into memory, then drops into a Python REPL for fast iterative queries.

```bash
# Basic
python -m rag_pipeline.serve

# With Gemini and classifier
GEMINI_API_KEY=xxx python -m rag_pipeline.serve --stream

# Skip classifier to save memory
python -m rag_pipeline.serve --no-classifier
```

Once inside the shell, everything is pre-loaded:

```python
# Minimal — just the query
run_pipeline("Find Nguyen-Roach from Feb 2021")
print(result["answer"])

# With Gemini answer
run_pipeline("Summarize all 2021 invoices", use_gemini=True)

# One-off hybrid retrieve
hybrid_retrieve("wine glasses")

# Parse without retrieving
parse_user_query("invoices over $500", vendor_lookup)

# Raw Gemini call
stream_print("Tell me a fun fact about invoices")
```

Available variables in the shell:

| Variable | Type | Description |
|---|---|---|
| `collection` | `chromadb.Collection` | Loaded collection with 998 vectors |
| `vendor_lookup` | `dict` | 493 vendor name mappings |
| `df_raw` | `pd.DataFrame` | Original CSV with OCRed Text column |
| `new_df` | `pd.DataFrame` | Normalized invoice data |
| `classifier` | `pipeline` or `None` | HF zero-shot classifier |
| `use_gemini` | `bool` | Whether Gemini client is available |

### 4. Demo — interactive full pipeline

```bash
GEMINI_API_KEY=xxx python -m rag_pipeline.demo
```

Pre-loads everything, then shows an interactive `>>` prompt:

```
>> Find the Nguyen-Roach invoice from February 2021

[parsed]
{
  "intent": "search_documents",
  "semantic_query": "nguyen roach",
  "chroma_where": {"$and": [{"doc_type": {"$eq": "invoice"}}, ...]}
}

[retrieved] 2 document(s)
  1. Nguyen-Roach — 2021-02-23 — $232.95
  2. Nguyen-Roach — 2021-02-23 — $232.95

[gemini]
The invoice from Nguyen-Roach dated February 23, 2021 (invoice #84652373)
includes items such as a Stemware Rack Display and Wine Glass Holder...
```

Type `exit` or Ctrl+C to quit.

### 5. In code (with auto-loading)

```python
from rag_pipeline.pipeline import run_pipeline

# Just the query — everything loads automatically
result = run_pipeline("Show invoices over $500")
print(result["answer"])

# With Gemini
result = run_pipeline("Which vendor has the highest total?", use_gemini=True)

# With classifier
from rag_pipeline.models import get_classifier
result = run_pipeline("Find paid invoices", classifier=get_classifier())
```

### 5. In code (explicit, no auto-loading)

```python
from rag_pipeline.normalize import load_and_normalize
from rag_pipeline.chroma_db import get_collection, build_vendor_lookup
from rag_pipeline.pipeline import run_pipeline, hybrid_retrieve, parse_user_query

new_df, df_raw = load_and_normalize("path/to.csv")
collection = get_collection()
vendor_lookup = build_vendor_lookup(new_df)

result = hybrid_retrieve("wine glasses", collection, vendor_lookup)
parsed = parse_user_query("invoices over $500", vendor_lookup)
```

## Pipeline flow

```
User query
  → classify_finance()        [optional HF zero-shot]
  → parse_user_query()        [rule-based → chroma_where + semantic_query]
  → needs_referee()           [heuristic: skip LLM when confident]
  → call_referee_llm()        [optional HF/Gemini validation]
  → hybrid_retrieve()         [ChromaDB query + post-filter amounts]
  → answer_query()            [Gemini or format_answer]
```
