# LLM Referee (`referee.py`)

## Purpose

The rule-based query parser (query_parser.py) is fast but sometimes wrong — it might miss a vendor, misinterpret a date, or fail to extract an amount threshold. The LLM referee validates and corrects the parser output when uncertainty is detected.

## When is the referee invoked?

`needs_referee()` (referee.py:24-41) returns True in three cases:

1. **No metadata filters parsed** — `chroma_where` is None (parser found nothing)
2. **Amount keywords without parsed values** — user said "over" or "$" but parser didn't extract an amount
3. **Month keywords without date filters** — user said "February" but no date range was set

```python
def needs_referee(user_query, parsed):
    if parsed.get("chroma_where") is None:
        return True
    has_amount = parsed.get("amount_gt") is not None or parsed.get("amount_lt") is not None
    if ("over" in q or "$" in q) and not has_amount:
        return True
    for month in months:
        if month in q and no_date_filter_in_parsed:
            return True
    return False
```

## Referee prompt

`REFEREE_PROMPT` is a structured JSON-instruct prompt that tells the LLM to:
- Compare the parser output JSON against the original user query
- Flag incorrect fields with error codes
- Produce a corrected parser output
- Follow ChromaDB filter syntax exactly

```python
REFEREE_PROMPT = """
You are a strict information-extraction referee...
Expected output schema: { is_valid, errors, corrected: { intent, semantic_query, chroma_where, ... }, field_checks }
Original user prompt: {user_query}
Parser output JSON: {parser_json}
"""
```

## Execution

`call_referee_llm()` (referee.py:99-128):

```python
if genai_client:
    response = genai_client.models.generate_content(model=model_name, contents=prompt)
elif llm_pipe:
    out = llm_pipe(messages, max_new_tokens=512, temperature=0.0)
```

- If Gemini is available → use it (more capable)
- If not → use the local SmolLM2-135M pipeline (may struggle with JSON output)
- Strips markdown code fences before JSON parsing

## Integration in pipeline

```python
# pipeline.py
if needs_referee(user_query, parsed):
    referee_result = call_referee_llm(user_query, parsed, llm_pipe=llm_pipe, genai_client=genai)
    if referee_result.get("is_valid"):
        parsed = referee_result["corrected"]  # use corrected parse
```

## Related files

| File | Role |
|---|---|
| `rag_pipeline/referee.py` | `needs_referee()` + `call_referee_llm()` + `REFEREE_PROMPT` |
| `rag_pipeline/pipeline.py` | Calls referee after parsing, before retrieval |
| `rag_pipeline/query_parser.py` | The parser whose output is being validated |
