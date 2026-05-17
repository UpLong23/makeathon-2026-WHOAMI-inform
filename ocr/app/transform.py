import json
import logging
import re

from groq import Groq

from app.config import REQUIRED_FIELDS, LLM_MODEL, LLM_TIMEOUT, logger

logger = logging.getLogger(__name__)


def structure_for_llm(raw_text: str) -> str:
    seller_lines = []
    client_lines = []
    general_lines = []

    for line in raw_text.split("\n"):
        if not line.strip():
            continue
        if "\t" in line and "Date" not in line:
            parts = [p.strip() for p in line.split("\t", 1)]
            left = parts[0] if len(parts) > 0 else ""
            right = parts[1] if len(parts) > 1 else ""
            if left:
                seller_lines.append(left)
            if right:
                client_lines.append(right)
        else:
            general_lines.append(line.strip())

    structured = ""
    if seller_lines:
        structured += "=== SELLER BLOCK ===\n"
        structured += "\n".join(seller_lines) + "\n\n"
    if client_lines:
        structured += "=== CLIENT BLOCK ===\n"
        structured += "\n".join(client_lines) + "\n\n"
    if general_lines:
        structured += "=== INVOICE DETAILS ===\n"
        structured += "\n".join(general_lines) + "\n"

    return structured


def _build_prompt(structured_text: str) -> str:
    return f"""
You are an invoice field extractor. The input is raw OCR text — it may be jumbled, out of order, or have broken formatting. Do NOT read it top-to-bottom. Scan the ENTIRE text to find each field by its meaning.

FIELDS TO EXTRACT:
- Seller Name: Who issued/sold. A company or person name. Never an address, never the buyer.
- Seller Tax ID: Tax or VAT ID of the seller. Usually near the seller's name or address block.
- Client Name: Who is being billed. A company or person name. Never an address, never the seller.
- Client Tax ID: Tax or VAT ID of the client. Usually near the client's name or address block.
- Invoice Number: A reference code for this invoice. Often labeled "Invoice no", "Invoice #", "Ref".
- Invoice Date: When the invoice was issued. Return as YYYY-MM-DD only.
- Net Worth: Amount before tax. A number. Often labeled "Net worth", "Subtotal", "Net amount".
- VAT: The tax amount in currency, not percentage. Often labeled "VAT", "Tax amount".
- Gross Worth: Final total after tax. Often labeled "Gross worth", "Total", "Amount due".

NUMBER EXTRACTION RULES (apply before returning any number):
- OCR inserts spaces inside large numbers — always remove them first: "1 612,50" → 1612.50
- Comma is often a decimal separator — convert to dot: "1.612,50" → 1612.50
- Strip all currency symbols: $, €, £
- Return as plain float, never a string

SELF-CORRECTION:
- Net Worth + VAT must equal Gross Worth (within 0.01 tolerance)
- If they don't balance, one number is corrupted by OCR — derive it:
  Net Worth = Gross Worth - VAT
  VAT = Gross Worth - Net Worth
  Gross Worth = Net Worth + VAT
- Use whichever two values you are most confident about to fix the third

OUTPUT: Return raw JSON only. No markdown. No explanation. Use exact field names above. null for missing fields.

OCR TEXT:
{structured_text}
"""


def extract_fields_llm(structured_text: str, client: Groq) -> dict:
    prompt = _build_prompt(structured_text)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
        timeout=LLM_TIMEOUT,
    )
    content = response.choices[0].message.content
    return json.loads(content)


def regex_extraction_fallback(structured_text: str) -> dict:
    def get_block(label: str) -> str:
        m = re.search(
            rf"=== {label}.*?===\n(.*?)(?====|\Z)", structured_text, re.DOTALL
        )
        return m.group(1).strip() if m else ""

    def find(pattern: str, text: str) -> str | None:
        m = re.search(pattern, text, re.I | re.MULTILINE)
        return m.group(1).strip() if m else None

    def clean_num(val: str | None) -> float | None:
        if not val:
            return None
        val = re.sub(r"[$€£\s]", "", val).replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return None

    seller = get_block("SELLER")
    client = get_block("CLIENT")
    details = get_block("INVOICE DETAILS")

    return {
        "Seller Name": find(r"^([A-Za-z][\w\s\-\.]+)$", seller),
        "Seller Tax ID": find(r"Tax\s*Id[:\\s]+([0-9\-]+)", seller),
        "Client Name": find(r"^([A-Za-z][\w\s\-\.]+)$", client),
        "Client Tax ID": find(r"Tax\s*Id[:\\s]+([0-9\-]+)", client),
        "Invoice Number": find(r"Invoice\s*no[:\\s]+([A-Z0-9\-]+)", details),
        "Invoice Date": find(r"(\d{2}[/\-]\d{2}[/\-]\d{4})", details),
        "Net Worth": clean_num(
            find(r"Total\s+\$?\s*([\d\s,\.]+?)\s+\$", details)
        ),
        "VAT": clean_num(
            find(r"Total\s+\$?[\d\s,\.]+\$\s*([\d\s,\.]+?)\s+\$", details)
        ),
        "Gross Worth": clean_num(
            find(r"Total\s+.*\$\s*([\d\s,\.]+)$", details)
        ),
    }


def extract_fields(structured_text: str, client: Groq) -> dict:
    regex_fields = regex_extraction_fallback(structured_text)

    try:
        llm_fields = extract_fields_llm(structured_text, client)
        for field in REQUIRED_FIELDS:
            if not llm_fields.get(field) and regex_fields.get(field):
                logger.info(
                    "'%s' null from LLM → filled by regex: %s",
                    field, regex_fields[field],
                )
                llm_fields[field] = regex_fields[field]
        return llm_fields
    except Exception as e:
        logger.warning("LLM failed entirely → using regex: %s", e)
        return regex_fields
