# WHOAMI INFORM — Financial Document Intelligence

WHOAMI INFORM is a financial-document analysis project built for the Makeathon 2026 **INFORM** challenge. It combines OCR-oriented data handling, a Retrieval-Augmented Generation (RAG) pipeline, a backend API, and a React frontend so users can ask questions about invoices and related financial documents and get structured answers.

## Project description

### Selected challenge
This repository targets the **INFORM** challenge from Makeathon 2026.

### Problem solved
The project addresses a common finance workflow problem: invoices and similar documents are difficult to search, validate, reconcile, and query manually. The system ingests document data, stores vector embeddings in ChromaDB, parses user questions, retrieves the most relevant context, and generates answers through an LLM-powered pipeline.

## Technologies

### Languages
- Python
- TypeScript
- HTML/CSS

### Libraries and frameworks
- **Backend / AI:** FastAPI, Pydantic, ChromaDB, sentence-transformers, google-generativeai, python-dotenv, pandas, NumPy
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Experimentation:** Jupyter notebooks

## Repository structure

| Path | Purpose |
|---|---|
| `rag_pipeline/` | Main Python package for ingestion, retrieval, answer generation, API serving, and demo execution. |
| `frontend/` | React + Vite frontend for querying and reconciliation workflows. |
| `resources/` | Markdown documentation explaining the architecture step by step. |
| `misc/` | Planning notes, architecture docs, slides, and supporting material. |
| `invoices_chroma_db/` | Persisted Chroma vector database files. |
| `Validation_OCR.ipynb`, `data.ipynb`, `rag.ipynb` | Research and validation notebooks. |
| `batch1_1.csv` | Sample dataset / development input file. |
| `requirements.txt` | Python dependencies for the backend and RAG pipeline. |
| `test.py` | Lightweight local testing script. |

## File overview

### Root
- `README.md`: Main project documentation.
- `requirements.txt`: Python dependency list.
- `Validation_OCR.ipynb`: OCR validation notebook.
- `data.ipynb`: Data exploration notebook.
- `rag.ipynb`: RAG experimentation notebook.
- `batch1_1.csv`: Sample or working dataset.
- `test.py`: Local pipeline testing entry point.

### `rag_pipeline/`
- `__init__.py`: Package initializer.
- `config.py`: Loads environment variables and central configuration.
- `models.py`: Shared data models and schemas.
- `normalize.py`: Text/document normalization helpers.
- `ingest.py`: Ingestion entry point.
- `ingestion.py`: Supporting ingestion logic.
- `chroma_db.py`: ChromaDB setup and helper functions.
- `query.py`: Query orchestration helpers.
- `query_parser.py`: Parses and structures incoming queries.
- `referee.py`: Validation/referee stage for generated responses.
- `gemini_client.py`: Gemini API integration.
- `pipeline.py`: End-to-end RAG pipeline orchestration.
- `serve.py`: FastAPI app / backend server entry point.
- `demo.py`: Local demo runner.
- `README.md`: Notes specific to the RAG package.

### `frontend/`
- `package.json`: Frontend scripts and dependencies.
- `.env.example`: Example frontend environment variables.
- `vite.config.ts`: Vite configuration.
- `index.html`: Frontend HTML entry template.
- `src/main.tsx`: React bootstrap file.
- `src/App.tsx`: Main app container.
- `src/Sidebar.tsx`: Sidebar navigation component.
- `src/Reconciliation.tsx`: Reconciliation screen/component.
- `src/index.css`: Global styles.
- `metadata.json`, `global.d.ts`, `tsconfig.json`: Tooling metadata and TypeScript configuration.

### `resources/`
- `00_OVERVIEW.md`: Overall system overview.
- `01_DATA_INGESTION.md`: Ingestion flow.
- `02_QUERY_CLASSIFICATION.md`: Query classification logic.
- `03_QUERY_PARSER.md`: Query parsing.
- `04_LLM_REFEREE.md`: Referee/validation stage.
- `05_RETRIEVAL.md`: Retrieval strategy.
- `06_ANSWER_GENERATION.md`: Answer generation stage.
- `07_PIPELINE_ORCHESTRATION.md`: End-to-end orchestration.
- `08_BACKEND_API.md`: Backend API notes.
- `09_FRONTEND.md`: Frontend notes.

## Installation

### 1. Clone the repository
```bash
git clone -b uplong https://github.com/UpLong23/makeathon-2026-WHOAMI-inform.git
cd makeathon-2026-WHOAMI-inform
```

### 2. Create a virtual environment
```bash
python -m venv .venv
```

**Windows (PowerShell)**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### 3. Install backend dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure backend environment variables
Create a `.env` file in the **repository root** based on `.env.example`.

```env
GEMINI_API_KEY=your_gemini_api_key_here
CHROMA_DB_DIR=./invoices_chroma_db
HOST=0.0.0.0
PORT=8000
PYTHONPATH=.
```

### 5. Configure the frontend
Open a second terminal and run:

```bash
cd frontend
npm install
cp .env.example .env
```

Example frontend `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Running the application

### Run the backend
Open a terminal in the **repository root** and run:

```bash
uvicorn rag_pipeline.serve:app --reload --host 0.0.0.0 --port 8000
```

If you need to rebuild the vector database or re-run ingestion, stay in the repository root and run:

```bash
python -m rag_pipeline.ingest
```

### Run the frontend
Open another terminal in the **`frontend/`** folder and run:

```bash
npm run dev
```

The frontend will typically be available at `http://localhost:5173`.

## API setup
This project uses Gemini for at least part of the LLM workflow, so a valid `GEMINI_API_KEY` is required before the backend can run correctly. Do not commit the real `.env` file; commit only `.env.example` files with placeholder values.

## Notes for anyone using the repo
- Start the backend from the repository root.
- Start the frontend from the `frontend/` directory.
- Keep `invoices_chroma_db/` present if you want to use the prebuilt local Chroma database.
- Use the notebooks only for experimentation, not as the main app entry point.

## Presentation
You can add screenshots, a demo GIF, or a video link here later.