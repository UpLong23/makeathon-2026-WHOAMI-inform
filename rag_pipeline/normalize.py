import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd


def clean_string(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def to_decimal(value):
    value = clean_string(value)
    if value is None:
        return None
    try:
        cleaned = value.replace(",", "")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def to_float(value):
    dec = to_decimal(value)
    return float(dec) if dec is not None else None


def to_iso_date(value):
    value = clean_string(value)
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return None


def normalize_vendor_name(name):
    name = clean_string(name)
    if not name:
        return None
    return name.lower()


def normalize_invoice(data: dict) -> dict:
    invoice = data.get("invoice", {}) or {}
    items = data.get("items", []) or []
    subtotal_data = data.get("subtotal", {}) or {}
    payment = data.get("payment_instructions", {}) or {}

    vendor = clean_string(invoice.get("seller_name"))
    invoice_number = clean_string(invoice.get("invoice_number"))
    invoice_date = to_iso_date(invoice.get("invoice_date"))
    due_date = to_iso_date(invoice.get("due_date") or payment.get("due_date"))

    tax = to_float(subtotal_data.get("tax"))
    discount = to_float(subtotal_data.get("discount")) or 0.0
    total = to_float(subtotal_data.get("total"))

    computed_subtotal = None
    if total is not None:
        computed_subtotal = round(total - (tax or 0.0) + discount, 2)

    item_descs = " | ".join(
        item.get("description", "").replace("\\n", " ").strip()
        for item in items
        if item.get("description")
    )

    d = (
        f"Invoice {invoice_number} from {vendor} dated {invoice_date}. "
        f"Items: {item_descs}. "
        f"Total: {total} USD."
    )

    line_items = []
    for item in items:
        qty = to_float(item.get("quantity"))
        line_total = to_float(item.get("total_price"))
        unit_price = round(line_total / qty, 2) if qty and line_total is not None else None
        line_items.append({
            "description": clean_string(item.get("description")),
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    return {
        "doc_id": f"inv_{invoice_number}" if invoice_number else "inv_unknown",
        "doc_type": "invoice",
        "vendor": vendor,
        "vendor_normalized": normalize_vendor_name(vendor),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "USD",
        "subtotal": computed_subtotal,
        "tax": tax if tax is not None else 0.0,
        "total": total,
        "status": "open" if due_date else "unknown",
        "line_items": line_items,
        "raw_text": d,
    }


def series_json_to_df(s: pd.Series) -> pd.DataFrame:
    def parse(x):
        if pd.isna(x):
            return {}
        if isinstance(x, dict):
            return x
        if isinstance(x, str):
            return json.loads(x)
        return x
    return pd.json_normalize(s.map(parse), max_level=0)


def load_and_normalize(csv_path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    test = df["Json Data"].apply(lambda x: normalize_invoice(json.loads(x.strip())))
    new_df = series_json_to_df(test)
    new_df["filename"] = df["File Name"]
    new_df = new_df.loc[:, [
        "filename", "doc_id", "doc_type", "vendor", "vendor_normalized",
        "invoice_number", "invoice_date", "due_date", "currency",
        "subtotal", "tax", "total", "status", "line_items", "raw_text",
    ]]
    new_df["line_items"] = new_df["line_items"].astype(str)
    new_df["vendor_normalized"] = new_df["vendor"].apply(lambda x: x.lower())
    return new_df, df
