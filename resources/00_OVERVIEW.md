# FinDoc AI — System Overview

## What it does

A financial document OCR and RAG (Retrieval-Augmented Generation) system. Users provide invoice images (JPEG) which are OCR-extracted into structured JSON, then ingested into a vector database. Users ask natural-language questions about invoices, and the system retrieves relevant documents and generates answers.

**Stack:** Python, Tesseract OCR, Groq LLM, ChromaDB, HuggingFace Transformers, FastAPI, React + TypeScript + Vite

## High-level architecture

```
Invoice JPEG
    │
    ▼ ┌─────────────────┐
    ──▶│  OCR pipeline   │──→ Tesseract → LLM extraction → structured JSON
       │  (ocr/)         │
       └────────┬────────┘
                │ (JSON documents)
                ▼
       ┌─────────────────┐
       │  Data ingestion  │──→ Normalize → chunk → embed → upsert to ChromaDB
       │  (rag_pipeline/) │
       └──────────────────┘
                              ┌──────────────────────────────────────────┐
                              │                                          │
                              ▼                                          │
                         User query                                      │
                              │                                          │
                              ▼ ┌─────────────────┐                      │
                              ──▶│  Zero-shot       │──→ Not finance → X │
                                 │  classifier      │                    │
                                 └────────┬────────┘                    │
                                          │ (finance)                    │
                                          ▼                              │
                                 ┌─────────────────┐                    │
                                 │  Query parser    │──→ structured      │
                                 └────────┬────────┘    filters          │
                                          │                              │
                                          ▼                              │
                                 ┌─────────────────┐                    │
                                 │  LLM Referee     │──→ (optional)      │
                                 └────────┬────────┘  validates parser   │
                                          │                              │
                                          ▼                              │
                                 ┌─────────────────┐                    │
                                 │  Hybrid retrieve │──→ semantic search  │
                                 │  (ChromaDB)      │   + metadata       │
                                 └────────┬────────┘   filters           │
                                          │ (top-5 raw docs)             │
                                          ▼                              │
                                 ┌─────────────────┐                    │
                                 │  Answer gen      │──→ Gemini /         │
                                 └────────┬────────┘   SmolLM2-135M /    │
                                          │            format_answer     │
                                          │ (SSE stream)                 │
                                          ▼                              │
                                    React frontend                       │
                                 (markdown + file chips)                 │
                              └──────────────────────────────────────────┘
```

## Filesystem layout

```
ocr/                      # OCR pipeline: JPEG → structured JSON
    app/
        config.py         # Env vars, paths, model settings
        ocr.py            # Image preprocessing + Tesseract OCR
        transform.py      # LLM extraction (Groq) + regex fallback
        pipeline.py       # process_image() — end-to-end OCR orchestration
        schemas.py        # Pydantic InvoiceDocument model
        cli.py            # CLI: python -m app.cli input.jpeg output.json
    tests/
        test_pipeline.py  # Smoke test, parsing tests, failure handling
    requirements.txt

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

- **OCR-first pipeline** — Invoice JPEGs are processed by Tesseract OCR with Otsu thresholding and dilation, then text is sent to a Groq LLM (llama-3.1-8b-instant) for structured field extraction. Regex fallback handles cases where the LLM fails. The output is validated against ground truth per-field (see `11_OCR_VALIDATION.md`).
- **Memory-aware retrieval** — Conversation history (last 6 messages) is always kept. The zero-shot classifier uses dual label sets depending on whether history exists: `["finance", "non-finance"]` for fresh queries, `["search_documents", "continue_conversation"]` for follow-ups. This prevents re-retrieval on social replies or conversational follow-ups (see `10_MEMORY_DECISION.md`).
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
You are analyzing the FinDoc AI system, a financial document OCR and RAG system. I have provided detailed documentation files covering the full pipeline. Read ALL of them thoroughly and help me understand the system end-to-end.

Answer the following questions based on the provided documentation:

1. How does the OCR pipeline convert an invoice JPEG into structured JSON? What preprocessing is applied before Tesseract? How does the layout reconstruction work?

2. What is the LLM extraction step in the OCR pipeline and how does it handle failures? What regex fallback is used?

3. What were the validation results of the OCR pipeline against ground truth data? Which fields performed well and which need improvement?

4. What is the purpose of the zero-shot classifier at the start of the RAG pipeline? What model is used and how does it decide whether to proceed?

5. How does the memory-aware retrieval decision work? How does the classifier's label set change when conversation history exists, and why?

6. Explain how the query parser extracts structured filters from natural language. What types of filters can it extract (vendor, date, amount, doc_type, currency, status)?

7. What is the LLM Referee and when does it get invoked? What does it validate?

8. How does hybrid retrieval work in ChromaDB? How are semantic search and metadata filtering combined?

9. What is the "smart file filtering" mechanism (`_filter_referenced_docs`) and why was it added?

10. Compare the three answer generation paths: Gemini, local SmolLM2, and format_answer fallback. When is each used?

11. How does the FastAPI backend stream answers and file metadata to the frontend? What is the SSE protocol format?

12. Explain how the ingestion pipeline transforms invoice JSON data into ChromaDB vectors, including normalization, chunking into line_items/rawtext, and embedding.

13. What is the FinLang/finance-embeddings-investopedia model and why was it chosen over general-purpose embeddings?

14. How does the frontend parse SSE events and render markdown responses with file attachments?

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
