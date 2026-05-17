import re
import json
from datetime import datetime
from typing import Any, Optional

from rag_pipeline.config import MONTH_NAMES, STOPWORDS


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9\.]+", text.lower())


def month_range(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1)
    end_month = month + 1 if month < 12 else 1
    end_year = year if month < 12 else year + 1
    end = datetime(end_year, end_month, 1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _add_quarter_filter(filters: list, qnum: int, year: int):
    if qnum == 1:
        filters.append({"invoice_date_int": {"$gte": int(f"{year}0101")}})
        filters.append({"invoice_date_int": {"$lt": int(f"{year}0401")}})
    elif qnum == 2:
        filters.append({"invoice_date_int": {"$gte": int(f"{year}0401")}})
        filters.append({"invoice_date_int": {"$lt": int(f"{year}0701")}})
    elif qnum == 3:
        filters.append({"invoice_date_int": {"$gte": int(f"{year}0701")}})
        filters.append({"invoice_date_int": {"$lt": int(f"{year}1001")}})
    elif qnum == 4:
        filters.append({"invoice_date_int": {"$gte": int(f"{year}1001")}})
        filters.append({"invoice_date_int": {"$lt": int(f"{year + 1}0101")}})


def parse_user_query(query: str, vendor_lookup: dict) -> dict[str, Any]:
    q = query.lower()
    filters: list[dict] = []
    source_column: Optional[str] = None
    amount_gt: Optional[float] = None
    amount_lt: Optional[float] = None

    if "invoice" in q:
        filters.append({"doc_type": {"$eq": "invoice"}})
    elif "receipt" in q:
        filters.append({"doc_type": {"$eq": "receipt"}})

    if "line item" in q or "line_item" in q or "lineitems" in q or "items" in q:
        source_column = "line_items"
        filters.append({"source_column": {"$eq": "line_items"}})
    elif "raw text" in q or "rawtext" in q or "description" in q:
        source_column = "rawtext"
        filters.append({"source_column": {"$eq": "rawtext"}})

    sorted_vendor_keys = sorted(vendor_lookup.keys(), key=len, reverse=True)
    matched_vendor = None
    for keyword in sorted_vendor_keys:
        if keyword in q:
            matched_vendor = vendor_lookup[keyword]
            break
    if matched_vendor:
        filters.append({"vendor_normalized": {"$eq": matched_vendor}})

    inv_match = re.search(r"\b\d{6,10}\b", q)
    if inv_match:
        filters.append({"invoice_number": {"$eq": inv_match.group(0)}})

    if "$" in q or "usd" in q or "dollar" in q:
        filters.append({"currency": {"$eq": "USD"}})
    elif "\u20ac" in q or "eur" in q or "euro" in q:
        filters.append({"currency": {"$eq": "EUR"}})

    if "paid" in q:
        filters.append({"status": {"$eq": "paid"}})
    elif "unpaid" in q or "outstanding" in q or "overdue" in q:
        filters.append({"status": {"$in": ["unpaid", "outstanding", "overdue"]}})

    month_match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b",
        q,
    )
    if month_match:
        month_name = month_match.group(1)
        year = int(month_match.group(2))
        month = MONTH_NAMES[month_name]
        date_start, date_end = month_range(year, month)
        date_start_int = int(date_start.replace("-", ""))
        date_end_int = int(date_end.replace("-", ""))
        filters.append({"invoice_date_int": {"$gte": date_start_int}})
        filters.append({"invoice_date_int": {"$lt": date_end_int}})

    elif re.search(r"\bin\s+(\d{4})\b", q):
        year_match = re.search(r"\bin\s+(\d{4})\b", q)
        year = int(year_match.group(1))
        filters.append({"invoice_date_int": {"$gte": int(f"{year}0101")}})
        filters.append({"invoice_date_int": {"$lt": int(f"{year + 1}0101")}})

    elif re.search(r"\b[Qq][1-4]\s+\d{4}\b", q):
        q_match = re.search(r"\b([Qq])([1-4])\s+(\d{4})\b", q)
        qnum = int(q_match.group(2))
        year = int(q_match.group(3))
        _add_quarter_filter(filters, qnum, year)
    elif re.search(r"\b(\d+)(?:st|nd|rd|th)\s+quarter\s+(?:of\s+)?(\d{4})\b", q):
        q_match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+quarter\s+(?:of\s+)?(\d{4})\b", q)
        qnum = int(q_match.group(1))
        year = int(q_match.group(2))
        _add_quarter_filter(filters, qnum, year)
    elif re.search(r"\b(first|second|third|fourth)\s+quarter(?:\s+of\s+)?\s+(\d{4})\b", q):
        ordinal = {"first": 1, "second": 2, "third": 3, "fourth": 4}
        q_match = re.search(r"\b(first|second|third|fourth)\s+quarter(?:\s+of\s+)?\s+(\d{4})\b", q)
        qnum = ordinal[q_match.group(1)]
        year = int(q_match.group(2))
        _add_quarter_filter(filters, qnum, year)

    gt_match = re.search(r"(?:over|greater than|above|more than)\s*[$€]?\s*(\d+(?:\.\d+)?)", q)
    lt_match = re.search(r"(?:under|less than|below)\s*[$€]?\s*(\d+(?:\.\d+)?)", q)
    if gt_match:
        amount_gt = float(gt_match.group(1))
    if lt_match:
        amount_lt = float(lt_match.group(1))

    if len(filters) == 0:
        chroma_where = None
    elif len(filters) == 1:
        chroma_where = filters[0]
    else:
        chroma_where = {"$and": filters}

    ignored = (
        set(STOPWORDS)
        | set(MONTH_NAMES.keys())
        | {"invoice", "receipt", "usd", "eur", "dollar", "dollars",
           "euro", "euros", "over", "greater", "than", "above", "under",
           "less", "below", "paid", "unpaid", "line", "item", "items",
           "outstanding", "overdue", "raw", "text"}
    )
    tokens = tokenize(q)
    semantic_terms = [t for t in tokens if t not in ignored and not t.isdigit() and len(t) > 1]
    semantic_query = " ".join(semantic_terms) or query

    return {
        "intent": "search_documents",
        "semantic_query": semantic_query,
        "chroma_where": chroma_where,
        "source_column": source_column,
        "amount_gt": amount_gt,
        "amount_lt": amount_lt,
    }
