# FinDoc AI — System Overview

## What it does

A financial document RAG (Retrieval-Augmented Generation) system. Users ask natural-language questions about invoices, and the system retrieves relevant documents from a vector database and generates answers.

**Stack:** Python, ChromaDB, HuggingFace Transformers, FastAPI, React + TypeScript + Vite

## High-level architecture

```
User query
    │
    ▼ ┌─────────────────┐
    ──▶│  Zero-shot       │──→ Not finance → "Query does not appear finance-related."
       │  classifier      │
       └────────┬────────┘
                │ (finance)
                ▼
       ┌─────────────────┐
       │  Query parser    │──→ structured filters (vendor, date, amount, doc_type)
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  LLM Referee     │──→ (optional) validates/corrects parser output
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  Hybrid retrieve │──→ semantic search (embeddings) + metadata filters
       │  (ChromaDB)      │
       └────────┬────────┘
                │ (top-5 raw docs)
                ▼
       ┌─────────────────┐
       │  Answer gen      │──→ Gemini / SmolLM2-135M / format_answer fallback
       └────────┬────────┘
                │ (SSE stream)
                ▼
          React frontend
       (markdown + file chips)
```

## Filesystem layout

```
rag_pipeline/             # Core RAG logic (no framework deps)
    config.py             # Paths, model names, constants
    models.py             # Embedding function (FinLang) + classifier loader
    chroma_db.py          # ChromaDB client, collection, vendor lookup
    normalize.py          # Invoice JSON → flat DataFrame
    ingestion.py          # DataFrame → ChromaDB records
    pipeline.py           # run_pipeline() — end-to-end orchestration
    query_parser.py       # NL query → structured chroma_where filters
    referee.py            # Finance classifier + LLM validation ref
    gemini_client.py      # Gemini API streaming client
    query.py              # CLI entry point
    serve.py              # Interactive REPL
    ingest.py             # Ingestion CLI

backend/
    server.py             # FastAPI app, SSE streaming, session mgmt

frontend/
    src/
        App.tsx           # Chat UI, SSE parsing, model toggle, file chips
        index.css         # .markdown-body custom styles
```

## Key design decisions

- **Finance-first guard** — A zero-shot classifier (facebook/bart-large-mnli) checks whether the query is finance-related before doing any work. Irrelevant queries are rejected immediately.
- **Rule-based parser + LLM referee** — The query parser extracts structured filters (vendor, date, amount, doc_type) using regex patterns. If the parser output looks uncertain, an LLM validates and corrects it.
- **Hybrid retrieval** — Combines semantic search (768-dim FinLang embeddings) with metadata filtering (vendor, date range, doc type, amount thresholds).
- **Dual answer generation** — Uses Gemini (if API key available) or a local SmolLM2-135M-Instruct model, with a structured fallback.
- **SSE streaming** — Answers and file metadata are pushed to the frontend as Server-Sent Events.
- **Smart file filtering** — `_filter_referenced_docs()` checks which filenames' metadata appear in the LLM answer text, so only relevant files are sent to the UI.

---

# Notebook LM Prompt

Copy the following into [NotebookLM](https://notebooklm.google.com/) (or any RAG-over-docs tool) along with the rest of the files in this `resources/` directory and these optional external references:

```
You are analyzing the FinDoc AI system, a financial document RAG system. I have provided detailed documentation files covering the full pipeline. Read ALL of them thoroughly and help me understand the system end-to-end.

Answer the following questions based on the provided documentation:

1. What is the purpose of the zero-shot classifier at the start of the pipeline? What model is used and how does it decide whether to proceed?

2. Explain how the query parser extracts structured filters from natural language. What types of filters can it extract (vendor, date, amount, doc_type, currency, status)?

3. What is the LLM Referee and when does it get invoked? What does it validate?

4. How does hybrid retrieval work in ChromaDB? How are semantic search and metadata filtering combined?

5. What is the "smart file filtering" mechanism (`_filter_referenced_docs`) and why was it added?

6. Compare the three answer generation paths: Gemini, local SmolLM2, and format_answer fallback. When is each used?

7. How does the FastAPI backend stream answers and file metadata to the frontend? What is the SSE protocol format?

8. Explain how the ingestion pipeline transforms invoice JSON data into ChromaDB vectors, including normalization, chunking into line_items/rawtext, and embedding.

9. What is the FinLang/finance-embeddings-investopedia model and why was it chosen over general-purpose embeddings?

10. How does the frontend parse SSE events and render markdown responses with file attachments?

For each answer, cite the specific source file and line/function where the relevant logic is implemented. If the answer involves multiple files, list all of them.
```

### Suggested external references to include in Notebook LM

- [ChromaDB Documentation](https://docs.trychroma.com/) — vector database usage
- [HuggingFace Zero-Shot Classification](https://huggingface.co/tasks/zero-shot-classification) — how bart-large-mnli works
- [FinLang/finance-embeddings-investopedia](https://huggingface.co/FinLang/finance-embeddings-investopedia) — the embedding model on HF
- [SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) — local LLM
- [Google Gemini API](https://ai.google.dev/gemini-api/docs) — used for answer generation
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) — SSE implementation
- [react-markdown](https://github.com/remarkjs/react-markdown) — frontend markdown rendering
