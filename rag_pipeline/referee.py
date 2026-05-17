import json
from typing import Any, Optional

from rag_pipeline.config import CLASSIFIER_MODEL


def classify_finance(queries: list[str], classifier=None, threshold: float = 0.59) -> list[bool]:
    if classifier is None:
        return [True] * len(queries)
    results = classifier(
        queries,
        candidate_labels=["finance", "non-finance"],
        hypothesis_template="This request is about {}.",
    )
    out = [True] * len(queries)
    for idx, result in enumerate(results):
        if result["labels"][0] == "non-finance" and result["scores"][0] < threshold:
            out[idx] = True
        else:
            out[idx] = result["labels"][0] == "finance"
    return out


def needs_referee(user_query: str, parsed: dict) -> bool:
    q = user_query.lower()

    if parsed.get("chroma_where") is None:
        return True

    has_amount = parsed.get("amount_gt") is not None or parsed.get("amount_lt") is not None
    if ("over" in q or "greater" in q or "above" in q or "$" in q) and not has_amount:
        return True

    months = {"january", "february", "march", "april", "may", "june",
              "july", "august", "september", "october", "november", "december"}
    if any(m in q for m in months):
        flat = json.dumps(parsed.get("chroma_where", {}))
        if "$gte" not in flat and "$lt" not in flat:
            return True

    return False


REFEREE_PROMPT = (
    "You are a strict information-extraction referee.\n\n"
    "Your job is to validate whether a parsed finance query matches the original user request.\n"
    "You will receive:\n"
    "1. the original user prompt\n"
    "2. the parser output JSON\n\n"
    "You must compare the parser output against the user prompt and determine whether each extracted field is correct.\n\n"
    "Rules:\n"
    "- Be conservative.\n"
    "- Do not invent values that are not clearly supported by the user prompt.\n"
    "- If a field is missing from the user prompt, it must be null.\n"
    "- If a field in the parser output is wrong, fix it.\n"
    "- Preserve the intended schema exactly.\n"
    "- Return JSON only.\n"
    "- No markdown.\n"
    "- No explanation text outside JSON.\n\n"
    "Expected output schema:\n"
    "{\n"
    '  "is_valid": true,\n'
    '  "errors": [],\n'
    '  "corrected": {\n'
    '    "intent": "search_documents",\n'
    '    "semantic_query": "",\n'
    '    "chroma_where": null,\n'
    '    "source_column": null,\n'
    '    "amount_gt": null,\n'
    '    "amount_lt": null\n'
    "  },\n"
    '  "field_checks": {\n'
    '    "intent": {"ok": true, "reason": ""},\n'
    '    "semantic_query": {"ok": true, "reason": ""},\n'
    '    "chroma_where": {"ok": true, "reason": ""},\n'
    '    "source_column": {"ok": true, "reason": ""},\n'
    '    "amount_gt": {"ok": true, "reason": ""},\n'
    '    "amount_lt": {"ok": true, "reason": ""}\n'
    "  }\n"
    "}\n\n"
    "Validation policy:\n"
    '- "is_valid" is true only if all extracted fields are correct.\n'
    '- "errors" should contain short machine-readable error codes, e.g. ["wrong_doc_type", "wrong_vendor"]\n'
    '- "corrected" must contain the best corrected parse based only on the user prompt.\n'
    '- "chroma_where" uses ChromaDB operators: $eq, $gte, $lt, $in, $and.\n'
    '  Example: {"$and": [{"doc_type": {"$eq": "invoice"}}, {"vendor_normalized": {"$eq": "nguyen-roach"}}]}\n'
    '  Date ranges use invoice_date_int with integer values (YYYYMMDD), like: {"invoice_date_int": {"$gte": 20210201}}\n'
    '- "source_column" should be "line_items", "rawtext", or null (search all).\n'
    '- "amount_gt"/"amount_lt" are numeric thresholds for total amount.\n'
    '- "semantic_query" should contain only leftover meaningful search terms not already represented in chroma_where.\n'
    '- If a value is uncertain, set it to null and mark the relevant field check as not ok.\n\n'
    "Original user prompt:\n"
    "{user_query}\n\n"
    "Parser output JSON:\n"
    "{parser_json}"
)


def call_referee_llm(
    user_query: str,
    parsed: dict,
    llm_pipe=None,
    genai_client=None,
    model_name: str = "Qwen/Qwen2.5-3B-Instruct",
) -> dict:
    prompt = REFEREE_PROMPT.format(
        user_query=user_query,
        parser_json=json.dumps(parsed, indent=2, default=str),
    )

    if genai_client is not None:
        response = genai_client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = response.text
    elif llm_pipe is not None:
        messages = [{"role": "user", "content": prompt}]
        out = llm_pipe(messages, max_new_tokens=512, temperature=0.0)
        text = out[0]["generated_text"][-1]["content"]
    else:
        raise ValueError("Provide either llm_pipe or genai_client")

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())
