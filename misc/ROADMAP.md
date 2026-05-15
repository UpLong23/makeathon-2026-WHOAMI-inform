# FinDoc AI — Roadmap

## Architectural Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION PIPELINE                                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│  ┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌─────────────┐  │
│  │             │    │                  │    │                  │    │             │  │
│  │   INGEST    │───▶│   OCR + LAYOUT   │───▶│   CHUNKING +     │───▶│   VECTOR    │  │
│  │             │    │   EXTRACTION     │    │   EMBEDDING      │    │   STORE     │  │
│  │ PDF / JPEG  │    │                  │    │                  │    │             │  │
│  │             │    │ ┌──────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────┐ │  │
│  │ pdf2image   │    │ │ PaddleOCR /  │ │    │ │ HuggingFace  │ │    │ │ FAISS / │ │  │
│  │ @ 300 DPI   │    │ │ PP-Structure │ │    │ │ Embeddings   │ │    │ │ChromaDB │ │  │
│  │             │    │ │ (layout-     │ │    │ │ (text-embed- │ │    │ │         │ │  │
│  │             │    │ │  aware)      │ │    │ │  ding-ada-   │ │    │ │         │ │  │
│  │             │    │ │ OR           │ │    │ │  002 /       │ │    │ │         │ │  │
│  │             │    │ │ AWS Textract │ │    │ │ all-MiniLM)  │ │    │ │         │ │  │
│  │             │    │ └──────────────┘ │    │ └──────────────┘ │    │ └─────────┘ │  │
│  └─────────────┘    └──────────────────┘    └──────────────────┘    └──────┬──────┘  │
│                                                                           │          │
│                                    OFFLINE INDEXING                       │          │
│                                                                           │          │
└───────────────────────────────────────────────────────────────────────────┼──────────┘
                                                                            │
                                                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                               QUERY PIPELINE (ONLINE)                                  │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │             │    │                  │    │                  │    │              │   │
│  │   USER      │───▶│   RETRIEVAL      │───▶│   RERANK +       │───▶│   GENERATE   │   │
│  │   QUERY     │    │                  │    │   FILTER         │    │   (LLM)      │   │
│  │             │    │ ┌──────────────┐ │    │ ┌──────────────┐ │    │ ┌──────────┐ │   │
│  │ "Total      │    │ │ query →      │ │    │ │ relevance    │ │    │ │ Gemini / │ │   │
│  │ amount?"    │    │ │ embedding →  │ │    │ │ threshold    │ │    │ │ GPT-4o / │ │   │
│  │             │    │ │ top-k from   │ │    │ │ (≥0.75)      │ │    │ │ Ollama   │ │   │
│  │             │    │ │ vector store │ │    │ │              │ │    │ │          │ │   │
│  │             │    │ └──────────────┘ │    │ └──────────────┘ │    │ └──────────┘ │   │
│  └──────┬──────┘    └──────────────────┘    └──────────────────┘    └──────┬───────┘   │
│         │                                                                  │           │
│         └──────────────────────────────────────────────────────────────────┘           │
│                                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                                                                        │
                                                                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              GUARDRAILS & OUTPUT                                       │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────────────┐  │
│  │ STRICT PROMPT       │   │ CONFIDENCE          │   │ SOURCE CITATION             │  │
│  │ "Answer only from   │   │ THRESHOLD           │   │ "TechCorp_Invoice_03.pdf"   │  │
│  │  retrieved context" │   │ <0.75 → "Δεν       │   │ + line item reference        │  │
│  │                     │   │          γνωρίζω"   │   │                             │  │
│  └─────────────────────┘   └─────────────────────┘   └─────────────────────────────┘  │
│                                                                                        │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────────────┐  │
│  │ SELF-CHECK (LLM)   │   │ BOUNDING-BOX        │   │ CHAT MEMORY                 │  │
│  │ 2nd LLM call        │   │ VISUAL EVIDENCE     │   │ Follow-up context retention │  │
│  │ verifies answer is  │   │ PIL crop from OCR   │   │ (LangChain memory + session)│  │
│  │ grounded in context │   │ coords → embed      │   │                             │  │
│  └─────────────────────┘   └─────────────────────┘   └─────────────────────────────┘  │
│                                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                                                                        │
                                                                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            BONUS: BANK RECONCILIATION                                  │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │ Invoice      │───▶│ CSV Bank         │───▶│ Pandas join on   │───▶│ Status flag  │  │
│  │ total amount │    │ Statement        │    │ amount + date    │    │ Paid/Pending │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘    └──────────────┘  │
│                                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5-Stage Pipeline

| Stage | Components | Tools |
|---|---|---|
| **01 Data Prep** | PDF → high-res images; image preprocessing (deskew, denoise, contrast) | `pdf2image` (300 DPI), OpenCV, Pillow |
| **02 Extraction** | Layout-aware OCR; text detection + recognition per region; reading-order reconstruction; Markdown/JSON output | PaddleOCR + PP-Structure, or AWS Textract, Tesseract |
| **03 Vectorization** | Chunking (per line item / section); embedding → vector store | `text-embedding-ada-002`, `all-MiniLM-L6-v2`; FAISS / ChromaDB |
| **04 RAG Query** | Embed query → top-k retrieval → rerank → LLM generation with strict grounding | Gemini API / GPT-4o / Ollama; LangChain |
| **05 Evaluation** | Accuracy (golden set), latency, faithfulness (LLM-as-judge), token cost tracking | Custom eval harness |

---

## Caveats

### OCR / Extraction Caveats
- **Scan quality dependency**: OCR accuracy degrades sharply below 300 DPI, with skew, noise, or low contrast
- **Multi-format diversity**: Invoice layouts vary wildly across vendors; layout-aware models trained on one domain may fail on unseen formats
- **Handwriting**: Printed-text OCR fails on handwritten fields; dedicated HTR models needed
- **Table extraction**: Complex tables (merged cells, no borders) are easily corrupted during OCR → downstream errors
- **Language / Greek text**: Many OCR engines have weaker support for Greek; requires language-pack tuning
- **PaddleOCR on low-resource**: PP-Structure can be heavy to run locally; GPU recommended

### RAG / Retrieval Caveats
- **Chunk boundary issues**: A single line item may be split across chunks → incomplete context for LLM
- **Irrelevant retrieval**: Low-quality embeddings or small top-k may retrieve wrong chunks → hallucination risk
- **Re-ranking overhead**: Extra latency; must choose between speed and precision
- **Metadata loss**: Without page/bbox metadata preserved through pipeline, source citation breaks

### LLM / Generation Caveats
- **Hallucination despite guardrails**: Strict prompts reduce but do not eliminate hallucination; self-check LLM may also hallucinate
- **Cost / latency tradeoff**: GPT-4o is accurate but expensive; local models (Ollama) are free but less reliable
- **Token limits**: Large invoices + conversation history may exceed context windows
- **Greek-specific**: Greek prompts may produce worse results on English-pretrained models; Greek fine-tuned or multilingual models preferred

### Production Caveats
- **Session management**: Chat memory across restarts requires database persistence (PostgreSQL / Redis)
- **Scalability**: Vector store search degrades at millions of chunks without proper indexing (IVF, HNSW)
- **Security**: Invoices contain sensitive financial data; must ensure data isolation between users/tenants

---

## Improvements

### OCR Pipeline Improvements
1. **Hybrid OCR + VLM**: Use Tesseract for plain text regions and Vision-Language models (e.g., Donut, Pix2Struct) for semantically complex fields (total amount, vendor name)
2. **Post-OCR correction**: Run a small LLM pass (e.g., GPT-4o-mini) on extracted text with the original image crop as reference, to fix OCR errors
3. **Active learning loop**: Flag uncertain OCR regions (low confidence) for human review → fine-tune on corrections
4. **Table-specific extractor**: Dedicated table parser (Camelot, Tabula, or PaddleOCR table module) before general OCR

### RAG Improvements
5. **Hierarchical chunking**: Keep parent-child chunk relationships (page → section → line item) for better context retrieval
6. **Hybrid search**: Combine dense (embedding) + sparse (BM25) retrieval for better recall on exact numeric matches
7. **Query rewriting**: Preprocess user query with a lightweight LLM call to expand abbreviations or reformulate for retrieval
8. **Contextual compression**: After retrieving top-k chunks, use LLM to extract only relevant sentences before final generation
9. **Conversation memory persistence**: Store chat history in a database (not just session state) for cross-session continuity

### Anti-Hallucination Improvements
10. **Multi-stage verification**: After generation, run a checker LLM that verifies each claim against the retrieved chunks; reject if unsupported
11. **Confidence calibration**: Output a confidence score per answer based on retrieval score + LLM logprobs; show to user
12. **Citation with bounding-box**: Overlay OCR bounding-box coordinates on the original PDF page → user sees exact location
13. **Reflection loop**: Let the LLM critique its own answer and re-generate if inconsistencies found (Reflection pattern)

### Production Improvements
14. **Docker + orchestration**: Containerize each pipeline stage; use Kubernetes or docker-compose for scaling
15. **Async ingestion**: Queue-based document processing (Redis + Celery) for handling bulk uploads
16. **Caching**: Cache embedding results for identical queries (common in financial reviews)
17. **Observability**: Log retrieval scores, token usage, latency per query; alert on hallucination flags
18. **Tenant isolation**: Separate vector store collections / namespaces per customer

### Bonus Feature Enhancements
19. **Bank reconciliation fuzzy matching**: Allow approximate amount matching (within tolerance) for payments with fees/rounding
20. **Visual evidence gallery**: Show all relevant bounding-box snippets in a grid view for multi-field queries
21. **Proactive information**: Automatically surface payment status and due dates when an invoice is mentioned

---

## Recommended Tech Stack

| Layer | Primary Choice | Fallback / Alternative |
|---|---|---|
| OCR | PaddleOCR + PP-Structure | AWS Textract, Tesseract |
| Embeddings | `all-MiniLM-L6-v2` (local) | `text-embedding-ada-002` (OpenAI) |
| Vector Store | ChromaDB | FAISS, Qdrant, pgvector |
| LLM | Gemini API / GPT-4o-mini | Ollama (Mistral, Llama 3), GPT-4o |
| Framework | LangChain / LlamaIndex | Custom Python |
| Frontend | Streamlit | Flask + React |
| Infrastructure | Docker | docker-compose, Kubernetes |
| Eval | Custom golden-set harness | LangSmith, RAGAS |

---

## Evaluation Criteria (from challenge)

| Metric | Target |
|---|---|
| Accuracy on golden set | ≥ 90% |
| Median end-to-end latency | ≤ 2s |
| Grounding (citation per answer) | 100% |
| Hallucination rate | 0% (fall back to "Δεν γνωρίζω") |
| Out-of-scope rejection | Correctly refuse questions not grounded in documents |
