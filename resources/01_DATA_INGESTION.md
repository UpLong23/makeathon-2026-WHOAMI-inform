# Data Ingestion Pipeline

## Source

Kaggle dataset: [High-Quality Invoice Images for OCR](https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr)
- CSV at `~/.cache/kagglehub/.../batch1_1.csv` (499 invoice rows)
- JSON in `Json Data` column (OCR-extracted fields + line items)
- JPEG images in `batch1_1/` folder
- `OCRed Text` column with raw OCR output

## Step 1: Normalization (`normalize.py`)

`load_and_normalize()` reads the CSV, parses each row's `Json Data` with `normalize_invoice()`:

```python
def normalize_invoice(data: dict) -> dict:
    invoice = data.get("invoice", {}) or {}
    items = data.get("items", []) or []
    ...
    return {
        "doc_id": f"inv_{invoice_number}",
        "doc_type": "invoice",
        "vendor": vendor,
        "vendor_normalized": vendor.lower(),
        "invoice_number": ...,
        "invoice_date": to_iso_date(...),
        "total": to_float(...),
        "line_items": [...],
        "raw_text": f"Invoice {inv_no} from {vendor} dated {date}. Items: {items}. Total: {total} USD.",
    }
```

Key helpers:
- `to_iso_date()` — tries `%m/%d/%Y`, `%Y-%m-%d`, `%m-%d-%Y` formats
- `to_float()` — strips commas, converts to float
- `normalize_vendor_name()` — lowercases vendor names for matching

Returns two DataFrames: `new_df` (normalized fields) and `df_raw` (original columns + OCRed Text).

## Step 2: Record building (`ingestion.py`)

`build_records()` creates ChromaDB documents from the normalized DataFrame:

- Each invoice row produces **2 chunks** (one per source column):
  - `line_items` — itemized product descriptions
  - `rawtext` — invoice summary text
- Each chunk gets metadata: vendor, invoice_number, invoice_date, total, currency, status, filename, doc_id, invoice_date_int (YYYYMMDD for range queries)

```python
records = [
    {
        "id": f"{idx}_line_items",
        "document": "...",  # item descriptions
        "metadata": {vendor, invoice_number, ..., source_column: "line_items"}
    },
    {
        "id": f"{idx}_rawtext",
        "document": "...",  # raw summary
        "metadata": {..., source_column: "rawtext"}
    },
]
```

Total: 998 vectors (499 invoices × 2 chunks).

## Step 3: Embedding (`models.py`)

### FinLangEmbeddingFunction

Custom ChromaDB `EmbeddingFunction` using `FinLang/finance-embeddings-investopedia`:
- 768-dimensional embeddings
- Finance-domain fine-tuned (better for invoice text than general models like all-MiniLM)
- Singleton pattern — loads once, caches model instance
- Normalizes embeddings for cosine similarity

```python
class FinLangEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self.model.encode(
            list(input),
            normalize_embeddings=True,
            ...
        )
        return embeddings.tolist()
```

## Step 4: ChromaDB ingestion (`chroma_db.py` + `ingestion.py`)

```python
collection = get_collection()  # PersistentClient at invoices_chroma_db/
collection.upsert(
    ids=[r["id"] for r in batch],
    documents=[r["document"] for r in batch],
    metadatas=[r["metadata"] for r in batch],
)
```

- Collection name: `invoices`
- Distance metric: `cosine` (hnsw:space)
- Persistent storage at `invoices_chroma_db/`

## Step 5: Vendor lookup

`build_vendor_lookup()` creates a dict mapping vendor names (lowercased) to their normalized form. Used by the query parser to match user-provided vendor names:

```python
vendor_lookup = {
    "johnson, buckley and terry": "johnson, buckley and terry",
    "johnson, buckley and terry (original human-readable)": "johnson, buckley and terry",
    ...
}
```

## Related files

| File | Role |
|---|---|
| `rag_pipeline/config.py` | CSV_PATH, CHROMA_PATH, EMBED_MODEL, BATCH_SIZE |
| `rag_pipeline/normalize.py` | Normalize invoice JSON → DataFrame |
| `rag_pipeline/ingestion.py` | Build ChromaDB records, batch upsert |
| `rag_pipeline/chroma_db.py` | ChromaDB client, collection, vendor lookup |
| `rag_pipeline/models.py` | FinLangEmbeddingFunction, get_classifier |
| `rag_pipeline/ingest.py` | CLI entry point: `python -m rag_pipeline.ingest --recreate` |
