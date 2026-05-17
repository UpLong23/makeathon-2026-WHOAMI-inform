#!/usr/bin/env python3
"""
Query the RAG system.

Usage:
    python -m rag_pipeline.query "Find Nguyen-Roach from Feb 2021"
    python -m rag_pipeline.query -i                          # interactive
    python -m rag_pipeline.query "..." --stream              # stream Gemini answer
    python -m rag_pipeline.query "..." --parse-only          # show parsed query only
"""
import argparse
import json
import sys

from rag_pipeline.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Query the RAG invoice system")
    parser.add_argument("query", nargs="*", help="Query string")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive REPL mode")
    parser.add_argument("--stream", action="store_true", help="Use Gemini to stream an answer")
    parser.add_argument("--parse-only", action="store_true", help="Only show parsed query")
    args = parser.parse_args()

    if args.interactive:
        repl(args)
        return

    query = " ".join(args.query)
    if not query:
        parser.print_help()
        sys.exit(1)

    run_one(query, args)


def repl(args):
    print("Loading RAG pipeline (one-time)...")
    from rag_pipeline.chroma_db import get_collection
    from rag_pipeline.normalize import load_and_normalize
    from rag_pipeline.chroma_db import build_vendor_lookup
    from rag_pipeline.config import CSV_PATH
    new_df, df_raw = load_and_normalize(CSV_PATH)
    vendor_lookup = build_vendor_lookup(new_df)
    collection = get_collection()
    print(f"Ready. Collection has {collection.count()} vectors.")
    print("Enter queries (Ctrl+D to exit)\n")
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            run_one(line, args, preloaded=(collection, vendor_lookup, df_raw))
    except EOFError:
        pass


def run_one(query, args, preloaded=None):
    if args.parse_only:
        from rag_pipeline.query_parser import parse_user_query
        vendor_lookup = preloaded[1] if preloaded else None
        if vendor_lookup is None:
            from rag_pipeline.normalize import load_and_normalize
            from rag_pipeline.chroma_db import build_vendor_lookup
            from rag_pipeline.config import CSV_PATH
            new_df, _ = load_and_normalize(CSV_PATH)
            vendor_lookup = build_vendor_lookup(new_df)
        parsed = parse_user_query(query, vendor_lookup)
        print(json.dumps(parsed, indent=2, default=str))
        return

    run_pipeline(
        query,
        use_gemini=args.stream,
    )


if __name__ == "__main__":
    main()
