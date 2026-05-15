# FinDoc AI — Architecture Flowchart (Mermaid)

Copy the diagram block below into [draw.io](https://app.diagrams.net) (Insert → Advanced → Mermaid) or any Mermaid-compatible editor.

---

```mermaid
flowchart TB
    subgraph INGEST["01 — INGEST & PREPROCESS"]
        A1[PDF / JPEG Input] --> A2[pdf2image @ 300 DPI]
        A2 --> A3[Image Preprocessing<br/>deskew · denoise · contrast]
    end

    subgraph EXTRACT["02 — OCR + LAYOUT EXTRACTION"]
        B1[Preprocessed Image] --> B2[Layout-Aware OCR]
        B2 --> B3[Text Detection<br/>PaddleOCR / Tesseract]
        B2 --> B4[Layout Parsing<br/>PP-Structure / AWS Textract]
        B3 --> B5[Text Recognition<br/>per region]
        B4 --> B5
        B5 --> B6[Reading-Order<br/>Reconstruction]
        B6 --> B7[Structured Output<br/>Markdown / JSON]
        B6 --> B8[Bounding-Box Coords<br/>per line item]
    end

    subgraph VECTORIZE["03 — CHUNKING & VECTORIZATION"]
        C1[Structured Text] --> C2[Chunking<br/>by section / line item]
        C2 --> C3[Embedding Model<br/>all-MiniLM / ada-002]
        C3 --> C4[(Vector Store<br/>FAISS / ChromaDB)]
        C5[(Metadata Store<br/>page · bbox · source)]
        C4 --> C6[Offline Index Complete]
        C5 --> C6
    end

    B8 --> C5

    subgraph QUERY["04 — RETRIEVAL & GENERATION"]
        D1[User Query] --> D2[Query Embedding]
        D2 --> D3[Top-k Retrieval<br/>from Vector Store]
        D3 --> D4{Reranker<br/>relevance + confidence}
        D4 -->|score ≥ 0.75| D5[LLM Generation<br/>Gemini / GPT-4o / Ollama]
        D4 -->|score < 0.75| D6[Fallback<br/>Δεν γνωρίζω]
        D5 --> D7[Self-Check<br/>2nd LLM verifies grounding]
        D7 -->|passes| D8[Final Answer]
        D7 -->|fails| D6
    end

    subgraph GUARDRAILS["GUARDRAILS"]
        G1[Strict Context Prompt]
        G2[Confidence Threshold ≥ 0.75]
        G3[Source Citation]
        G4[Self-Check Pass]
    end

    subgraph OUTPUT["OUTPUT ENRICHMENT"]
        E1[Final Answer] --> E2[Citation<br/>filename + line item]
        E1 --> E3[Bounding-Box Crop<br/>PIL crop → embed in response]
        E4[Chat Memory<br/>LangChain + session state]
        E5[Bank Reconciliation<br/>Pandas join with CSV statement]
    end

    subgraph EVAL["05 — EVALUATION"]
        F1[Golden Set<br/>50 Q&A pairs] --> F2[Accuracy ≥ 90%]
        F3[Latency Tracking] --> F4[Median ≤ 2s]
        F5[Faithfulness Check<br/>LLM-as-judge] --> F6[0 hallucinations]
        F7[Token Cost Logging] --> F8[Cost per query]
    end

    INGEST --> EXTRACT
    EXTRACT --> VECTORIZE
    VECTORIZE --> QUERY
    QUERY --> OUTPUT
    GUARDRAILS -.-> QUERY
    OUTPUT -.-> EVAL
```

---

## Alternative: Horizontal Layout (better for wide screens)

```mermaid
flowchart LR
    subgraph PIPELINE["FinDoc AI Pipeline"]
        direction LR
        P1["📄 Ingest<br/>PDF/JPEG"] -->
        P2["🔍 Extract<br/>OCR + Layout"] -->
        P3["🧠 Vectorize<br/>Chunk + Embed"] -->
        P4["💬 Retrieve +<br/>Generate"] -->
        P5["✅ Output<br/>Answer + Evidence"]
    end

    subgraph GUARD["Anti-Hallucination Layer"]
        G1[Strict Prompt]
        G2[Confidence ≥ 0.75]
    end

    subgraph BONUS["Bonus Features"]
        B1[Follow-up Chat]
        B2[Bounding-Box Visual]
        B3[Bank Reconciliation]
    end

    PIPELINE --> GUARD
    GUARD --> BONUS
```

---

## Individual Component Flow (detailed)

```mermaid
flowchart TD
    subgraph DATA_PREP["Data Preparation"]
        DP1[PDF Scan] --> DP2[pdf2image 300 DPI]
        DP2 --> DP3[Grayscale]
        DP3 --> DP4[Denoise]
        DP4 --> DP5[Deskew]
        DP5 --> DP6[Contrast Enhancement]
    end

    subgraph OCR_PIPELINE["Layout-Aware OCR Pipeline"]
        OC1[Clean Image] --> OC2[Layout Detection<br/>PP-Structure]
        OC2 --> OC3{Region Type}
        OC3 -->|Text Block| OC4[PaddleOCR<br/>Text Recognition]
        OC3 -->|Table| OC5[Table Extraction<br/>PaddleOCR Table Module]
        OC3 -->|Figure/Title| OC6[Label & Skip]
        OC4 --> OC7[Reading-Order<br/>Reconstruction]
        OC5 --> OC7
        OC7 --> OC8[Markdown Export]
        OC7 --> OC9[JSON Export<br/>with bbox coords]
    end

    subgraph VECTOR["Vectorization"]
        VE1[Chunked Text<br/>+ Metadata] --> VE2[Embedding<br/>HuggingFace / OpenAI]
        VE2 --> VE3[(ChromaDB<br/>or FAISS)]
    end

    subgraph RAG["RAG Query Engine"]
        RQ1[User Question] --> RQ2[Embed Query]
        RQ2 --> RQ3[Similarity Search<br/>top-k]
        RQ3 --> RQ4[Re-rank]
        RQ4 --> RQ5{Confidence ≥ 0.75?}
        RQ5 -->|Yes| RQ6[LLM Generation<br/>with Context]
        RQ5 -->|No| RQ7["→ Δεν γνωρίζω"]
        RQ6 --> RQ8[Self-Check<br/>LLM-as-judge]
        RQ8 -->|Pass| RQ9[Answer + Citation]
        RQ8 -->|Fail| RQ7
    end

    DATA_PREP --> OCR_PIPELINE
    OCR_PIPELINE --> VECTOR
    VECTOR --> RAG
```

---

## How to use with drawio

1. Open [app.diagrams.net](https://app.diagrams.net)
2. Click **Arrange** → **Insert** → **Advanced** → **Mermaid**
3. Paste any of the diagrams above
4. Click **Insert** — the diagram will render as editable shapes
