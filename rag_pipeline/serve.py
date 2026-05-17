#!/usr/bin/env python3
"""
Pre-load all models into memory, then enter an interactive query loop.

Usage:
    GEMINI_API_KEY=xxx python -m rag_pipeline.serve
    python -m rag_pipeline.serve --no-classifier  # skip classifier load
    python -m rag_pipeline.serve --stream          # use Gemini for answers
"""
import argparse
import code
import sys

from rag_pipeline.config import CSV_PATH
from rag_pipeline.normalize import load_and_normalize
from rag_pipeline.chroma_db import get_collection, build_vendor_lookup
from rag_pipeline.models import FinLangEmbeddingFunction, get_classifier


def main():
    parser = argparse.ArgumentParser(description="Pre-load RAG pipeline and enter REPL")
    parser.add_argument("--no-classifier", action="store_true", help="Skip loading classifier")
    parser.add_argument("--stream", action="store_true", help="Use Gemini for answers")
    args = parser.parse_args()

    # Warm up models
    print("Warming up...")
    emb_fn = FinLangEmbeddingFunction()
    print(f"  Embedding model loaded: {emb_fn.model_name}")

    classifier = None
    if not args.no_classifier:
        try:
            classifier = get_classifier()
            print("  Classifier loaded")
        except Exception as e:
            print(f"  Classifier skipped: {e}")

    collection = get_collection()
    print(f"  ChromaDB collection '{collection.name}': {collection.count()} vectors")

    new_df, df_raw = load_and_normalize(CSV_PATH)
    vendor_lookup = build_vendor_lookup(new_df)
    print(f"  Data: {len(new_df)} invoices, {len(vendor_lookup)} vendors")

    if args.stream:
        from rag_pipeline.gemini_client import get_client
        try:
            get_client()
            use_gemini = True
            print("  Gemini client ready")
        except ValueError as e:
            print(f"  Gemini skipped: {e}")
            use_gemini = False
    else:
        use_gemini = False

    # Inject into interactive namespace
    namespace = {
        "collection": collection,
        "vendor_lookup": vendor_lookup,
        "df_raw": df_raw,
        "new_df": new_df,
        "classifier": classifier,
        "use_gemini": use_gemini,
        "run_pipeline": __import__("rag_pipeline.pipeline", fromlist=["run_pipeline"]).run_pipeline,
        "hybrid_retrieve": __import__("rag_pipeline.pipeline", fromlist=["hybrid_retrieve"]).hybrid_retrieve,
        "parse_user_query": __import__("rag_pipeline.query_parser", fromlist=["parse_user_query"]).parse_user_query,
        "format_answer": __import__("rag_pipeline.pipeline", fromlist=["format_answer"]).format_answer,
        "stream_print": __import__("rag_pipeline.gemini_client", fromlist=["stream_print"]).stream_print,
    }

    print("\nAll models loaded. Dropping into interactive shell.")
    print("Available: collection, vendor_lookup, df_raw, classifier, run_pipeline(), etc.")
    banner = f"RAG Pipeline ({collection.count()} vectors, {len(vendor_lookup)} vendors) — Ctrl+D to exit"

    code.interact(banner=banner, local=namespace)


if __name__ == "__main__":
    main()
