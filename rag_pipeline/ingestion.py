import pandas as pd
from tqdm import tqdm

from rag_pipeline.config import BATCH_SIZE
from rag_pipeline.chroma_db import get_collection, delete_collection


def build_records(new_df):
    col1, col2 = new_df.columns[-2], new_df.columns[-1]
    records = []

    for idx, row in new_df.iterrows():
        inv_date_str = row.get("invoice_date", "")
        inv_date_int = None
        if pd.notna(inv_date_str) and str(inv_date_str).strip():
            try:
                inv_date_int = int(str(inv_date_str).replace("-", ""))
            except ValueError:
                pass

        meta_base = {
            "filename":          str(row.get("filename",           "")),
            "doc_id":            str(row.get("doc_id",             "")),
            "doc_type":          str(row.get("doc_type",           "")),
            "vendor":            str(row.get("vendor",             "")),
            "vendor_normalized": str(row.get("vendor_normalized",  "")),
            "invoice_number":    str(row.get("invoice_number",     "")),
            "invoice_date":      str(row.get("invoice_date",       "")),
            "invoice_date_int":  inv_date_int,
            "currency":          str(row.get("currency",           "")),
            "subtotal": float(row["subtotal"]) if pd.notna(row.get("subtotal")) else 0.0,
            "tax":      float(row["tax"])      if pd.notna(row.get("tax"))      else 0.0,
            "total":    float(row["total"])    if pd.notna(row.get("total"))    else 0.0,
            "status":            str(row.get("status",             "")),
        }

        for field in [col1, col2]:
            text = str(row[field]).strip() if pd.notna(row[field]) else ""
            if not text or text.lower() in ("nan", "none", ""):
                continue
            records.append({
                "id": f"{idx}_{field}",
                "document": text,
                "metadata": {**meta_base, "source_column": field},
            })

    return records


def ingest_data(new_df, recreate=False):
    if recreate:
        delete_collection()

    collection = get_collection()
    records = build_records(new_df)

    print(f"Total chunks: {len(records)}")

    for i in tqdm(range(0, len(records), BATCH_SIZE), desc="Inserting batches"):
        batch = records[i : i + BATCH_SIZE]
        collection.upsert(
            ids=[r["id"] for r in batch],
            documents=[r["document"] for r in batch],
            metadatas=[r["metadata"] for r in batch],
        )

    print(f"Done! '{collection.name}' contains {collection.count()} vectors.")
    return collection
