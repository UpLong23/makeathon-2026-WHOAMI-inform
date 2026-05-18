# OCR Invoice Extractor

Takes a JPEG invoice image, runs Tesseract OCR, sends the extracted text to an LLM
(Groq), and produces a structured JSON document.

## Project Structure

```
ocr/
  app/
    __init__.py
    config.py        # Environment variables, paths, model settings
    ocr.py           # Image loading, preprocessing, Tesseract OCR
    transform.py     # LLM prompt building, LLM call, regex fallback
    pipeline.py      # Orchestration: JPEG → JSON
    schemas.py       # Pydantic output model
    cli.py           # CLI entrypoint
  tests/
    test_pipeline.py # Smoke test, parsing tests, failure tests
  requirements.txt
  README.md
```

## Setup

### 1. Install Tesseract OCR

- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
- **macOS:** `brew install tesseract`
- **Windows:** Download from [GitHub UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

### 2. Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM inference |
| `TESSERACT_CMD` | No | `tesseract` | Path to Tesseract binary |
| `LLM_MODEL` | No | `llama-3.1-8b-instant` | Groq model name |
| `DEFAULT_CURRENCY` | No | `EUR` | Default currency for output |
| `LLM_TIMEOUT` | No | `30` | LLM request timeout in seconds |

## Usage

```bash
export GROQ_API_KEY="gsk_..."
python -m app.cli input.jpeg output.json
```

Optional currency override:

```bash
python -m app.cli input.jpeg output.json --currency USD
```

## Example output

```json
{
  "doc_id": "inv_001",
  "doc_type": "invoice",
  "vendor": "Acme Corp",
  "vendor_normalized": "acme corp",
  "invoice_number": "INV-12345",
  "invoice_date": "2024-01-15",
  "currency": "EUR",
  "subtotal": 1000.0,
  "tax": 200.0,
  "total": 1200.0,
  "status": "captured",
  "line_items": [],
  "raw_text": "... OCR output ...",
  "client_name": "Beta LLC",
  "client_tax_id": "987-65-4321",
  "seller_tax_id": "123-45-6789"
}
```

## Tests

```bash
cd ocr
pytest tests/
```

## Containerization

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y tesseract-ocr
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ app/
ENTRYPOINT ["python", "-m", "app.cli"]
```
