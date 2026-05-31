import datetime


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
        'Gross Worth': None
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

    def extract_three_numbers_after_total(text):
        """
        Extracts the first 3 numeric values after "Total" keyword.
        Handles missing/inconsistent currency symbols.
        Returns (net_worth, vat, gross_worth) as floats or (None, None, None).
        """
        # Find Total line
        total_match = re.search(r'Total\s+(.*?)(?:\n|$)', text, re.IGNORECASE)
        if not total_match:
            return None, None, None

        total_line = total_match.group(1)

        # Extract all numeric sequences (including spaces and commas)
        numbers = re.findall(r'[\d\s,]+(?:\.\d+)?', total_line)

        if len(numbers) < 3:
            return None, None, None

        # Take first 3 numbers
        net = clean_num(numbers[0])
        vat = clean_num(numbers[1])
        gross = clean_num(numbers[2])

        return net, vat, gross

    # Try to extract monetary values
    net, vat, gross = extract_three_numbers_after_total(ocred_text)

    extracted['Net Worth'] = net
    extracted['VAT'] = vat
    extracted['Gross Worth'] = gross

    if net is None:
        print(
            f"⚠️  Could not extract monetary values from Invoice Number: {extracted['Invoice Number']}")

    return extracted


def extract_date_components(date_str):
    """
    Extract date components (year, month, day) from various date formats.
    Returns a tuple of (year, month, day) as integers, or None if parsing fails.
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
            dt = datetime.strptime(date_str, date_format)
            return (dt.year, dt.month, dt.day)
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
                    dt = datetime.strptime(
                        date_str, '%d/%m/%Y' if '/' in date_str else '%d-%m-%Y')
                    return (dt.year, dt.month, dt.day)
                except:
                    pass
            # If second value > 12, it must be day (MM/DD/YYYY format)
            elif second > 12:
                try:
                    dt = datetime.strptime(
                        date_str, '%m/%d/%Y' if '/' in date_str else '%m-%d-%Y')
                    return (dt.year, dt.month, dt.day)
                except:
                    pass
            # Both <= 12: ambiguous, try MM/DD/YYYY first (US format)
            else:
                for date_format in formats:
                    try:
                        dt = datetime.strptime(date_str, date_format)
                        return (dt.year, dt.month, dt.day)
                    except:
                        continue

    # Try other formats as fallback
    fallback_formats = [
        '%m-%d-%Y',      # MM-DD-YYYY
        '%d-%m-%Y',      # DD-MM-YYYY
    ]

    for date_format in fallback_formats:
        try:
            dt = datetime.strptime(date_str, date_format)
            return (dt.year, dt.month, dt.day)
        except:
            continue

    return None
