import json
from typing import Any, Optional

import chromadb

from rag_pipeline.config import CSV_PATH, TOP_K
from rag_pipeline.query_parser import parse_user_query
from rag_pipeline.referee import classify_finance, needs_referee, call_referee_llm
from rag_pipeline.gemini_client import answer_query as gemini_answer, get_client as get_gemini
from rag_pipeline.config import GEMINI_MODEL

_cache = {}

def _ensure_data():
    if "collection" not in _cache:
        from rag_pipeline.chroma_db import get_collection, build_vendor_lookup
        from rag_pipeline.normalize import load_and_normalize
        _cache["collection"] = get_collection()
        new_df, df_raw = load_and_normalize(CSV_PATH)
        _cache["vendor_lookup"] = build_vendor_lookup(new_df)
        _cache["df_raw"] = df_raw
    return _cache["collection"], _cache["vendor_lookup"], _cache["df_raw"]


def _ensure_classifier():
    if "classifier" not in _cache:
        try:
            from rag_pipeline.models import get_classifier
            _cache["classifier"] = get_classifier()
        except Exception:
            _cache["classifier"] = None
    return _cache["classifier"]


def post_filter_amounts(results: dict, amount_gt: Optional[float], amount_lt: Optional[float]) -> dict:
    if amount_gt is None and amount_lt is None:
        return results
    kept_ids, kept_docs, kept_metas, kept_dists = [], [], [], []
    for doc_id, doc, meta, dist in zip(
        results["ids"][0], results["documents"][0],
        results["metadatas"][0], results["distances"][0],
    ):
        try:
            total = float(meta.get("total", 0))
        except (ValueError, TypeError):
            total = 0.0
        if amount_gt is not None and total <= amount_gt:
            continue
        if amount_lt is not None and total >= amount_lt:
            continue
        kept_ids.append(doc_id)
        kept_docs.append(doc)
        kept_metas.append(meta)
        kept_dists.append(dist)
    return {
        "ids": [kept_ids], "documents": [kept_docs],
        "metadatas": [kept_metas], "distances": [kept_dists],
    }


def hybrid_retrieve(
    user_query: str,
    collection: chromadb.Collection,
    vendor_lookup: dict,
    n_results: int = 5,
) -> dict[str, Any]:
    parsed = parse_user_query(user_query, vendor_lookup)

    # print("\n[PARSED QUERY]")
    # print(json.dumps(parsed, indent=2, default=str))

    query_kwargs: dict[str, Any] = {
        "query_texts": [parsed["semantic_query"]],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }

    if parsed["chroma_where"]:
        query_kwargs["where"] = parsed["chroma_where"]

    results = collection.query(**query_kwargs)

    results = post_filter_amounts(results, parsed["amount_gt"], parsed["amount_lt"])

    return {
        "parsed": parsed,
        "results": results,
    }


def format_answer(user_query: str, output: dict) -> str:
    results = output["results"]
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    if not ids:
        return "No documents matched your query."

    lines = [f"Query: {user_query}", f"Found {len(ids)} result(s):\n"]
    for rank, (doc_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists), 1):
        lines.append(f"  Result #{rank}  (cosine distance: {dist:.4f})")
        lines.append(f"  ID             : {doc_id}")
        lines.append(f"  Source column  : {meta.get('source_column')}")
        lines.append(f"  Vendor         : {meta.get('vendor')}")
        lines.append(f"  Invoice #      : {meta.get('invoice_number')}")
        lines.append(f"  Date           : {meta.get('invoice_date')}")
        lines.append(f"  Total          : {meta.get('total')} {meta.get('currency')}")
        lines.append(f"  Status         : {meta.get('status')}")
        lines.append(f"  Text snippet   : {doc[:200]}...\n")
    return "\n".join(lines)


def run_pipeline(
    user_query: str,
    collection=None,
    vendor_lookup: Optional[dict] = None,
    df_raw=None,
    classifier=None,
    llm_pipe=None,
    use_gemini: bool = False,
    n_results: int = TOP_K,
) -> dict:
    collection, vendor_lookup, df_raw = _ensure_data()
    if classifier is None:
        classifier = _ensure_classifier()

    step_classify = {"passed": True, "message": ""}
    if classifier:
        is_finance = classify_finance([user_query], classifier)[0]
        if not is_finance:
            msg = "Query does not appear finance-related."
            print(msg)
            step_classify = {"passed": False, "message": msg}
            return {"steps": step_classify, "answer": msg}

    parsed = parse_user_query(user_query, vendor_lookup)
    step_parse = {"passed": True, "parsed": parsed}

    step_referee = {"called": False, "result": None}
    if needs_referee(user_query, parsed):
        try:
            genai = None
            if use_gemini:
                try:
                    genai = get_gemini()
                except Exception:
                    pass
            referee_result = call_referee_llm(
                user_query, parsed,
                llm_pipe=llm_pipe,
                genai_client=genai,
                model_name=GEMINI_MODEL if genai else None,
            )
            if referee_result.get("is_valid"):
                parsed = referee_result["corrected"]
            step_referee = {"called": True, "result": referee_result}
        except Exception as e:
            step_referee = {"called": True, "error": str(e)}

    output = hybrid_retrieve(user_query, collection, vendor_lookup, n_results=n_results)
    step_retrieve = {"passed": True, "n_results": len(output["results"]["ids"][0])}
    
    # print(output['results']['metadatas'])
    
    docs_retrieved = set([doc_name['filename'] for doc_name in output['results']['metadatas'][0]])
    print(docs_retrieved)

    filenames = [m["filename"] for m in output["results"]["metadatas"][0]]
    ocr_docs = df_raw[df_raw["File Name"].isin(filenames)]["OCRed Text"].tolist()

    answer = None
    if use_gemini and ocr_docs:
        try:
            answer = gemini_answer(user_query, ocr_docs)
        except Exception as e:
            print(f"\n[Gemini error: {e}]")
    if answer is None:
        if llm_pipe and ocr_docs:
            docs_text = "\n---\n".join(
                f"Document {i+1}:\n{doc[:2000]}" for i, doc in enumerate(ocr_docs)
            )
            from rag_pipeline.gemini_client import ANSWER_PROMPT
            prompt = ANSWER_PROMPT.format(user_query=user_query, documents_text=docs_text)
            messages = [{"role": "user", "content": prompt}]
            out = llm_pipe(messages, max_new_tokens=512, temperature=0.0)
            answer = out[0]["generated_text"][-1]["content"]
            print(answer)
        else:
            answer = format_answer(user_query, output)
            print(answer)

    return {
        "steps": step_classify,
        "parse": step_parse,
        "referee": step_referee,
        "retrieve": step_retrieve,
        "answer": answer,
        "docs_retrieved": docs_retrieved,
    }
