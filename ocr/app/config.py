import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
TESSERACT_CMD: str = os.environ.get("TESSERACT_CMD", "tesseract")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")
DEFAULT_CURRENCY: str = os.environ.get("DEFAULT_CURRENCY", "EUR")
LLM_TIMEOUT: int = int(os.environ.get("LLM_TIMEOUT", "30"))

REQUIRED_FIELDS: list[str] = [
    "Seller Name", "Seller Tax ID", "Client Name", "Client Tax ID",
    "Invoice Number", "Invoice Date", "Net Worth", "VAT", "Gross Worth",
]
