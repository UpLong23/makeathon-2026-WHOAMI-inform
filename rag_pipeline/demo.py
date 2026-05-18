#!/usr/bin/env python3
"""
Interactive demo — full pipeline from prompt to Gemini answer.

Usage:
    GEMINI_API_KEY=xxx python -m rag_pipeline.demo

Pre-loads everything at startup, then loops:
    You type → classify → parse → retrieve → Gemini answers (streaming)
"""
import sys

from rag_pipeline.pipeline import run_pipeline
from rag_pipeline.config import GEMINI_API_KEY
from rag_pipeline.chroma_db import get_collection
from rag_pipeline.normalize import load_and_normalize
from rag_pipeline.chroma_db import build_vendor_lookup
from rag_pipeline.config import CSV_PATH
from rag_pipeline.models import get_classifier


def main():
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        print("  export GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    print("Loading RAG pipeline...")
    collection = get_collection()
    new_df, df_raw = load_and_normalize(CSV_PATH)
    vendor_lookup = build_vendor_lookup(new_df)
    classifier = get_classifier()
    print(f"Ready — {collection.count()} vectors, {len(vendor_lookup)} vendors.\n")

    while True:
        try:
            query = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            break

        print()
        try:
            run_pipeline(query, use_gemini=True, classifier=classifier)
        except Exception as e:
            print(f"[Error: {e}]")
        print()


if __name__ == "__main__":
    main()
