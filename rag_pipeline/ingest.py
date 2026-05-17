#!/usr/bin/env python3
"""
Ingest invoice data into ChromaDB.

Usage:
    python -m rag_pipeline.ingest                     # upsert into existing collection
    python -m rag_pipeline.ingest --recreate          # drop and re-ingest
    python -m rag_pipeline.ingest --csv /path/to.csv  # custom CSV
"""
import argparse
import sys

from rag_pipeline.config import CSV_PATH
from rag_pipeline.normalize import load_and_normalize
from rag_pipeline.ingestion import ingest_data
from rag_pipeline.chroma_db import build_vendor_lookup


def main():
    parser = argparse.ArgumentParser(description="Ingest invoices into ChromaDB")
    parser.add_argument("--csv", default=str(CSV_PATH), help="Path to CSV file")
    parser.add_argument("--recreate", action="store_true", help="Drop collection before ingesting")
    args = parser.parse_args()

    print(f"Loading data from {args.csv}...")
    new_df, df_raw = load_and_normalize(args.csv)
    print(f"Loaded {len(new_df)} invoices")

    vendor_lookup = build_vendor_lookup(new_df)
    print(f"Built vendor lookup with {len(vendor_lookup)} entries")

    collection = ingest_data(new_df, recreate=args.recreate)

    print("\nIngestion complete. Collection ready for queries.")
    print(f"  vendor_lookup has {len(vendor_lookup)} entries")
    print(f"  df_raw has {len(df_raw)} rows")


if __name__ == "__main__":
    main()
