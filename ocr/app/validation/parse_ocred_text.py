import datetime
import re


import re
import json


import re
import json


def parse_line_items(ocred_text: str) -> list:

    match = re.search(r"Gross worth\s*(.*?)\s*SUMMARY", ocred_text, re.DOTALL)
    if not match:
        return []
    truncated_text = match.group(1)

    # Clean OCR noise: digits fused onto end of words e.g. "Pulitzer8" -> "Pulitzer"
    truncated_text = re.sub(r'(?<=[a-zA-Z])\d+(?=\s)', '', truncated_text)

    def normalize_number(s: str) -> str:
        return s.replace(" ", "").replace(",", ".")

    # First pass: find all item start positions by detecting "N." or sequential "N " pattern
    # Use a single pattern anchored on "each" to find all items
    item_pattern = re.compile(
        r"(\d+)\.?\s+"                           # item number (captured)
        r"(.*?)"                                  # prefix description (lazy)
        r"(\d{1,4},\d{2})\s+each\s+"             # quantity
        r"([\d][\d\s]*,\d{2})\s+"                # net_price
        r"[\d][\d\s]*,\d{2}\s+"                  # junk net_worth — discard
        r"(\d+%)\s+"                              # VAT
        r"([\d][\d\s]*,\d{2})\s*",               # gross_worth
        re.DOTALL
    )

    # Collect all matches first so we know their spans
    matches = list(item_pattern.finditer(truncated_text))

    line_items = []

    for i, m in enumerate(matches):
        item_num = int(m.group(1))
        prefix_desc = m.group(2).strip()
        quantity = normalize_number(m.group(3))
        net_price = normalize_number(m.group(4))
        vat = m.group(5).strip()
        gross_worth = normalize_number(m.group(6))

        # Suffix: everything from end of this match to start of next match
        # (or end of string), but ONLY if the next match is sequential (item_num + 1)
        end_of_this = m.end()
        if i + 1 < len(matches):
            next_match = matches[i + 1]
            next_num = int(next_match.group(1))
            if next_num == item_num + 1:
                # Suffix is text between end of numeric fields and start of next item
                suffix_desc = truncated_text[end_of_this:next_match.start()].strip(
                )
            else:
                # Next "match" isn't the sequential item — don't grab suffix
                suffix_desc = ""
        else:
            # Last item — take everything remaining
            suffix_desc = truncated_text[end_of_this:].strip()

        net_worth = f"{float(quantity) * float(net_price):.2f}"
        full_desc = re.sub(r"\s+", " ", f"{prefix_desc} {suffix_desc}").strip()

        line_items.append({
            "description": full_desc,
            "quantity":    quantity,
            "net_price":   net_price,
            "net_worth":   net_worth,
            "vat":         vat,
            "gross_worth": gross_worth,
        })

    return line_items


def transform_fields_ocred_to_json(extracted_dict) -> dict:
    domain_mapping = {
        'Seller Name': 'vendor_normalized',
        'Client Name': 'client_name',
        'Seller Tax ID': 'seller_tax_id',
        'Client Tax ID': 'client_tax_id',
        'Invoice Number': 'invoice_number',
        'Invoice Date': 'invoice_date',
        'Net Worth': 'subtotal',
        'VAT': 'tax',
        'Gross Worth': 'total',
        'Line Items': 'line_items'
    }

    # Transform: old_key → new_key, but keep all values intact
    return {domain_mapping.get(old_key, old_key): value for old_key, value in extracted_dict.items()}


def parse_ocred_text(ocred_text):
    """
    Extract key fields from OCRed Text ground truth.
    Returns a dictionary with extracted values.
    """
    extracted = {
        'Seller Name': None,
        'Client Name': None,
        'Seller Tax ID': None,
        'Client Tax ID': None,
        'Invoice Number': None,
        'Invoice Date': None,
        'Net Worth': None,
        'VAT': None,
        'Gross Worth': None,
        'Line Items': [None]
    }

    # Tax ID pattern (XXX-XX-XXXX format)
    tax_id_pattern = r'\d{3}-\d{2}-\d{4}'

    # Invoice number pattern (8 digits)
    invoice_num_pattern = r'Invoice\s+(?:no|number):\s*(\d+)'

    # Date patterns (MM/DD/YYYY or YYYY-MM-DD or variations)
    date_patterns = [
        r'Date\s+of\s+issue:\s*(\d{1,2}/\d{1,2}/\d{4})',
        r'Date\s+of\s+issue:\s*(\d{4}-\d{1,2}-\d{1,2})',
    ]

    # Money pattern (dollar amounts)
    money_pattern = r'[\$\s]*(\d+\.?\d*)'

    lines = ocred_text.split('\n')
    # print(lines)

    # Extract invoice number
    for line in lines:
        match = re.search(invoice_num_pattern, line, re.IGNORECASE)
        if match:
            extracted['Invoice Number'] = match.group(1)
            break

    # Extract date
    for line in lines:
        for pattern in date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                extracted['Invoice Date'] = match.group(1)
                break
        if extracted['Invoice Date']:
            break

    # Extract items
    extracted['Line Items'] = parse_line_items(ocred_text)
    # print(extracted['Line Items'])
    # exit(0)

    # Extract tax IDs (looking for two of them - seller and client)
    tax_ids = re.findall(tax_id_pattern, ocred_text)
    if len(tax_ids) >= 1:
        extracted['Seller Tax ID'] = tax_ids[0]
    if len(tax_ids) >= 2:
        extracted['Client Tax ID'] = tax_ids[1]

    # Extract seller and client names (usually appear before Tax Id labels)
    seller_match = re.search(r'Seller:\s*([^\n]+)', ocred_text, re.IGNORECASE)
    if seller_match:
        extracted['Seller Name'] = seller_match.group(1).strip()

    client_match = re.search(r'Client:\s*([^\n]+)', ocred_text, re.IGNORECASE)
    if client_match:
        extracted['Client Name'] = client_match.group(1).strip()

    # Extract monetary values from Total line
    def clean_num(val):
        """Clean numeric value: remove spaces, convert comma to dot, convert to float"""
        if not val:
            return None
        val = re.sub(r'[$€£\s]', '', val).replace(',', '.')
        try:
            return float(val)
        except:
            return None

    def extract_three_numbers_after_total(ocred_text: str):
        """
        Extracts subtotal, tax, and total from the Total line.
        Returns (subtotal, tax, total) as floats or (None, None, None).
        """

        def normalize_number(s: str) -> float:
            return float(s.replace(" ", "").replace(",", "."))

        # Grab everything after "Total" on that line
        total_match = re.search(r'Total\s+(.*?)(?:\n|$)',
                                ocred_text, re.IGNORECASE)
        if not total_match:
            return None, None, None

        total_line = total_match.group(1)

        # Extract all European-formatted numbers (digits, optional spaces, comma, 2 decimals)
        numbers = re.findall(r'\d[\d\s]*,\d{2}', total_line)

        if len(numbers) < 3:
            return None, None, None

        subtotal = normalize_number(numbers[0])  # 1 335,86 -> 1335.86
        tax = normalize_number(numbers[1])  # 133,59   -> 133.59
        total = normalize_number(numbers[2])  # 1 469,45 -> 1469.45

        return subtotal, tax, total

    # print(ocred_text)
    # print("\n")
    # Try to extract monetary values
    net, vat, gross = extract_three_numbers_after_total(ocred_text)
    print("\n\nTOTAL VALUES RETURNED")
    # print(net)
    # print(vat)
    # print(gross)
    # exit(0)

    extracted['Net Worth'] = net
    extracted['VAT'] = vat
    extracted['Gross Worth'] = gross

    if net is None:
        print(
            f"⚠️  Could not extract monetary values from Invoice Number: {extracted['Invoice Number']}")

    return transform_fields_ocred_to_json(extracted)


def extract_date_components(date_str):
    """
    Extract date components from various date formats.
    Returns a string formatted as MM/DD/YYYY (e.g., '09/04/2019'), or None if parsing fails.
    Intelligently handles ambiguous formats like X/Y/YYYY by checking if values > 12.
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # First, try unambiguous formats
    unambiguous_formats = [
        '%Y-%m-%d',      # YYYY-MM-DD (unambiguous)
        '%Y/%m/%d',      # YYYY/MM/DD (unambiguous)
    ]

    for date_format in unambiguous_formats:
        try:
            dt = datetime.datetime.strptime(date_str, date_format)
            return dt.strftime('%m/%d/%Y')
        except:
            continue

    # For ambiguous formats (X/Y/YYYY or X-Y-YYYY), try to disambiguate
    ambiguous_patterns = [
        (r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', ['%m/%d/%Y', '%d/%m/%Y']),
    ]

    for pattern, formats in ambiguous_patterns:
        match = re.match(pattern, date_str)
        if match:
            first, second, year = match.groups()
            first, second = int(first), int(second)

            # If first value > 12, it must be day (DD/MM/YYYY format)
            if first > 12:
                try:
                    dt = datetime.datetime.strptime(
                        date_str, '%d/%m/%Y' if '/' in date_str else '%d-%m-%Y')
                    return dt.strftime('%m/%d/%Y')
                except:
                    pass
            # If second value > 12, it must be day (MM/DD/YYYY format)
            elif second > 12:
                try:
                    dt = datetime.datetime.strptime(
                        date_str, '%m/%d/%Y' if '/' in date_str else '%m-%d-%Y')
                    return dt.strftime('%m/%d/%Y')
                except:
                    pass
            # Both <= 12: ambiguous, try MM/DD/YYYY first (US format)
            else:
                for date_format in formats:
                    try:
                        dt = datetime.datetime.strptime(date_str, date_format)
                        return dt.strftime('%m/%d/%Y')
                    except:
                        continue

    # Try other formats as fallback
    fallback_formats = [
        '%m-%d-%Y',      # MM-DD-YYYY
        '%d-%m-%Y',      # DD-MM-YYYY
    ]

    for date_format in fallback_formats:
        try:
            dt = datetime.datetime.strptime(date_str, date_format)
            return dt.strftime('%m/%d/%Y')
        except:
            continue

    return None
