from rag_pipeline.config import GEMINI_API_KEY, GEMINI_MODEL


_client = None

def get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set. Export it or set in config.py")
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def stream_print(prompt: str, model: str = GEMINI_MODEL) -> str:
    client = get_client()
    full = ""
    for i, chunk in enumerate(client.models.generate_content_stream(
        model=model, contents=prompt
    ), 1):
        print(chunk.text, end="", flush=True)
        full += chunk.text
    print()
    return full


# ANSWER_PROMPT = (
#     "You are a strict financial document analyst.\n\n"
#     "Step 1 — Relevance check: Determine whether ANY of the retrieved documents "
#     "are related to the user's query. If none of the documents contain information "
#     "remotely relevant to the query, respond with: "
#     '"The retrieved documents are not related to your question." '
#     "and stop. Do not make up information.\n\n"
#     "Step 2 — Answer: If the documents ARE relevant, answer using ONLY the provided documents. "
#     "Cite specific invoice numbers, vendors, dates, and amounts when relevant. "
#     "Be concise and direct. If the documents only partially answer the question, "
#     "say what is missing.\n\n"
#     "User query:\n"
#     "{user_query}\n\n"
#     "Retrieved documents:\n"
#     "{documents_text}\n\n"
#     "Answer:"
# )


ANSWER_PROMPT = (
    "You are a financial document analyst. Answer the user's question using ONLY the provided documents.\n\n"
    "Rules:\n"
    "- Base your answer strictly on the documents below.\n"
    "- If the documents do not contain the information requested, say so.\n"
    "- Cite specific invoice numbers, vendors, dates, and amounts when relevant.\n"
    "- Be concise and direct.\n\n"
    "User query:\n"
    "{user_query}\n\n"
    "Retrieved documents:\n"
    "{documents_text}\n\n"
    "Answer:"
)


def answer_query(user_query: str, retrieved_docs: list[str], model: str = GEMINI_MODEL) -> str:
    docs_text = "\n---\n".join(
        f"Document {i+1}:\n{doc[:2000]}" for i, doc in enumerate(retrieved_docs)
    )
    prompt = ANSWER_PROMPT.format(
        user_query=user_query,
        documents_text=docs_text,
    )
    return stream_print(prompt, model=model)
