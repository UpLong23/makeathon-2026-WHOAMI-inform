import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# KAGGLE_PATH = Path.home() / ".cache" / "kagglehub" / "datasets" / "osamahosamabdellatif" / "high-quality-invoice-images-for-ocr" / "versions" / "3"
# CSV_PATH = KAGGLE_PATH / "batch_1" / "batch_1" / "batch1_1.csv"
CSV_PATH = BASE_DIR.parent / "batch_1" / "batch_1" / "batch1_1.csv"
CHROMA_PATH = BASE_DIR / "invoices_chroma_db"
COLLECTION_NAME = "invoices"

# EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# EMBED_DEVICE = "cpu"
CLASSIFIER_MODEL = "facebook/bart-large-mnli"
BATCH_SIZE = 64
TOP_K = 5

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3-flash-preview"

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

STOPWORDS = {
    "show", "me", "find", "the", "a", "an", "from", "for", "of", "in",
    "all", "with", "documents", "document", "please", "get", "list",
    "give", "search", "look", "fetch",
}

if __name__=='__main__':
    print(BASE_DIR)
