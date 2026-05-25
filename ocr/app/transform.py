import json
import logging
import re

from groq import Groq

from config import REQUIRED_FIELDS, LLM_MODEL, LLM_TIMEOUT, logger

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
You are an expert invoice field extractor. Your task is to identify and extract numeric financial fields from messy OCR text.

CRITICAL INVOICE STRUCTURE:
Every invoice has exactly ONE "Total" line that contains the three financial amounts you need.
This Total line appears at the end of the invoice (NOT in summary sections or headers).
Format: "Total" keyword followed by exactly 3 numeric values in this EXACT order:
  1st value = Net Worth (subtotal before tax)
  2nd value = VAT/Tax Amount (tax in currency units, NOT percentage)
  3rd value = Gross Worth (final total after adding tax)

IMPORTANT: The Total line has multiple currency symbols separated by spaces. Parse left-to-right, extracting exactly 3 amounts.

REAL EXAMPLES FROM ACTUAL INVOICES (use these as reference):
Example 1:
  Line: "Total    $ 84 944,82 $ 8 494,48 $ 93 439,30"
  → Net Worth: 84944.82
  → VAT: 8494.48
  → Gross Worth: 93439.30
  (Note: "$ 84 944,82" has space before the number AND space inside the number)

Example 2:
  Line: "Total	$4 819,90 $ 481,99 $5 301,89"
  → Net Worth: 4819.90
  → VAT: 481.99
  → Gross Worth: 5301.89
  (Note: "$4 819,90" - currency touches number but number has internal space)

Example 3:
  Line: "Total          $5 992,66   $ 599,27   $ 6 591,93"
  → Net Worth: 5992.66
  → VAT: 599.27
  → Gross Worth: 6591.93

PARSING ALGORITHM FOR TOTAL LINE:
1. Find the word "Total" in the text
2. Extract everything after "Total" on that line
3. Split by "$" symbol (this separates the 3 amounts)
4. You will get 4 parts: [empty prefix, amount1, amount2, amount3]
5. For each amount:
   a) Remove ALL whitespace (including internal spaces): " 84 944,82" → "84944,82"
   b) Replace comma with dot: "84944,82" → "84944.82"
   c) Convert to float: 84944.82
6. Return as: [amount1, amount2, amount3]

DISTINGUISH BETWEEN:
- SUMMARY section: Contains VAT percentage (e.g., "10%") — IGNORE THIS, it's not the amounts you need
- TOTAL line: Contains VAT amount in currency (€, $, £, or just numbers) — USE THIS
- Lines with "Subtotal" or "Net amount": May appear before Total — these are LESS reliable than Final Total

FIELDS TO EXTRACT:
- Seller Name: Company or person name on invoice (NOT address)
- Seller Tax ID: VAT/Tax ID near seller info
- Client Name: Billing customer name (NOT address)
- Client Tax ID: VAT/Tax ID near client info
- Invoice Number: Reference code (labeled "Invoice no", "Invoice #", "Ref", "Invoice ID", etc.)
- Invoice Date: When issued (return as YYYY-MM-DD only)
- Net Worth: First numeric value from FINAL Total line (amount before tax)
- VAT: Second numeric value from FINAL Total line (tax amount in currency, never a percentage)
- Gross Worth: Third numeric value from FINAL Total line (final total)

NUMBER CLEANING RULES (CRITICAL — apply to all amounts):
Step 1: Remove ALL spaces (both leading and internal): " 84 944,82" → "84944,82"
Step 2: Replace comma with dot if present: "84944,82" → "84944.82"
Step 3: Strip any remaining non-digit characters except the decimal point
Step 4: Convert to float

CRITICAL EXAMPLES OF NUMBER CLEANING:
- " 84 944,82" → remove spaces → "84944,82" → replace comma → 84944.82 ✓
- "$4 819,90" → remove $ → "4 819,90" → remove spaces → "4819,90" → replace comma → 4819.90 ✓
- "$ 481,99" → remove $ and space → "481,99" → replace comma → 481.99 ✓
- "$5 301,89" → remove $ → "5 301,89" → remove spaces → "5301,89" → replace comma → 5301.89 ✓
- "€1.234,50" → remove € → "1.234,50" → remove dot (thousands separator) → "1234,50" → replace comma → 1234.50 ✓

VALIDATION & SELF-CORRECTION:
After extraction, verify: Net Worth + VAT ≈ Gross Worth (within 0.1 tolerance to account for rounding)

If they don't balance, one value is corrupted:
- Example: Net=84944.82, VAT=8494.48, Gross=93939.30
- Check: 84944.82 + 8494.48 = 93439.30 (should be), but got 93939.30 (error of 500)
- This suggests Gross has OCR error. Fix: Gross = 84944.82 + 8494.48 = 93439.30

Priority for self-correction:
1. Trust the two values that are closest to matching when summed
2. If Net + VAT ≠ Gross:
   - Assume Gross is wrong: Gross = Net + VAT
   OR
   - Assume VAT is wrong: VAT = Gross - Net
   OR
   - Assume Net is wrong: Net = Gross - VAT

HANDLING AMBIGUOUS TEXT:
- If multiple "Total" lines exist, use the LAST one (it's the final total)
- Ignore lines with percentages (%), those are from SUMMARY sections
- Ignore "Subtotal" lines unless no "Total" exists
- ALWAYS count the exact number of "$" symbols to ensure you have exactly 3 amounts

OUTPUT FORMAT:
Return raw JSON only. No markdown. No explanation. Use exact field names. Use null for missing fields.
Return numbers as plain floats (not strings).
Return dates as YYYY-MM-DD strings.

Recheck your extraction:
- Did you find exactly 3 numeric amounts from the Total line?
- Did you remove ALL spaces from each amount?
- Did you convert commas to dots?
- Do the numbers add up correctly (Net + VAT ≈ Gross)?

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
