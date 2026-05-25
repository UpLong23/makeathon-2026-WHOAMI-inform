import os
import logging
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Get the project root (one level up from ocr/ notebook directory)
PROJECT_ROOT = Path(
    "/Users/grigoriostsakalis/Desktop/UniAI/makeathon-2026-WHOAMI-inform")
env_path = PROJECT_ROOT / "ocr" / ".data" / ".env"

# Explicitly point to the .env file (same pattern as RAG pipeline config.py)
load_dotenv(env_path)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise ValueError(
        f"❌ GROQ_API_KEY not found in {env_path}. Add it to backend/.env")
TESSERACT_CMD: str = os.environ.get("TESSERACT_CMD", "tesseract")
LLM_MODEL: str = os.environ.get(
    "LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
DEFAULT_CURRENCY: str = os.environ.get("DEFAULT_CURRENCY", "EUR")
LLM_TIMEOUT: int = int(os.environ.get("LLM_TIMEOUT", "30"))

REQUIRED_FIELDS: list[str] = [
    "Seller Name", "Seller Tax ID", "Client Name", "Client Tax ID",
    "Invoice Number", "Invoice Date", "Net Worth", "VAT", "Gross Worth",
]
