import pandas as pd
import chromadb

from rag_pipeline.config import CHROMA_PATH, COLLECTION_NAME
from rag_pipeline.models import FinLangEmbeddingFunction


_client = None

def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=FinLangEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


def delete_collection():
    try:
        get_client().delete_collection(COLLECTION_NAME)
        print(f"Deleted collection '{COLLECTION_NAME}'.")
    except Exception:
        pass


def build_vendor_lookup(new_df) -> dict:
    vendor_lookup = {
        row["vendor_normalized"]: row["vendor_normalized"]
        for _, row in new_df.iterrows()
        if pd.notna(row.get("vendor_normalized")) and row.get("vendor_normalized")
    }
    for _, row in new_df.iterrows():
        vendor = str(row.get("vendor", "")).strip().lower()
        normalized = row.get("vendor_normalized", "")
        if vendor and normalized:
            vendor_lookup[vendor] = normalized
    return vendor_lookup
