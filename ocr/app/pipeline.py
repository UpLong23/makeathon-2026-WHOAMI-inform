from groq import Groq

from config import DEFAULT_CURRENCY, REQUIRED_FIELDS, logger
from ocr import run_ocr
from transform import structure_for_llm, extract_fields
from schemas import InvoiceDocument


def _raw_text_modify(raw_text: str) -> str:
    """ Return Raw Text up until before the 
    items Section of the Recceipts"""
    raw_text_sliced = raw_text[:raw_text.index("ITEMS")]
    return raw_text_sliced


def _normalize_to_document(
    fields: dict,
    raw_text: str,
    idx: int = 1,
    currency: str = DEFAULT_CURRENCY,
) -> InvoiceDocument:
    vendor = fields.get("Seller Name")
    return InvoiceDocument(
        doc_id=f"inv_{idx:03d}",
        vendor=vendor,
        vendor_normalized=vendor.lower() if vendor else None,
        invoice_number=fields.get("Invoice Number"),
        invoice_date=fields.get("Invoice Date"),
        currency=currency,
        subtotal=_safe_float(fields.get("Net Worth")),
        tax=_safe_float(fields.get("VAT")),
        total=_safe_float(fields.get("Gross Worth")),
        client_name=fields.get("Client Name"),
        client_tax_id=fields.get("Client Tax ID"),
        seller_tax_id=fields.get("Seller Tax ID"),
        raw_text=_raw_text_modify(raw_text),
        line_items=fields.get("Line Items")
    )


def _safe_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def process_image(
    img_path: str,
    client: Groq,
    doc_index: int = 1,
    currency: str = DEFAULT_CURRENCY,
) -> InvoiceDocument:
    logger.info("Processing image: %s", img_path)

    raw_text = run_ocr(img_path)
    # print("---"*50)
    # print("RAW TEXT RETURNED:")
    # print(raw_text)
    # exit(0)
    structured_text = structure_for_llm(raw_text)
    # print("---"*50)
    # print(structured_text)
    # exit(0)
    fields = extract_fields(structured_text, client)

    # print("\n\n\nFIELDS ===")
    # print(fields, "\n")
    doc = _normalize_to_document(
        fields, raw_text, idx=doc_index, currency=currency)
    logger.info("Extracted document: %s", doc.doc_id)
    return doc
