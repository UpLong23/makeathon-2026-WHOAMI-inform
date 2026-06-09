from parse_ocred_text import parse_ocred_text, extract_date_components
from compare import strict_compare, fuzzy_compare
import pandas as pd
import json
import re
# python library that helps compare similarities between two texts
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import warnings
warnings.filterwarnings('ignore')


"""
    This script includes the functions required to validate the output of the
    "ocr ecosystem" made with python.

    It retrieves the appropriate invoice, if exists, and checks the validity of the data.
"""
FUZZY_MATCH_THRESHOLD = 90
STRICT_NUMERIC_TOLERANCE = 0.1


def validate_ocr_results(batch_df, output_json, domains=None, tolerance=STRICT_NUMERIC_TOLERANCE, fuzzy_threshold=FUZZY_MATCH_THRESHOLD):
    """
    Validate OCR results against ground truth.

    Parameters:
    -----------
    domains : str or list of str, optional
        Specific domain(s) to validate. If None, validates all available domains.
        Available domains: 'Seller Name', 'Client Name', 'Seller Tax ID',
                          'Client Tax ID', 'Invoice Number', 'Invoice Date',
                          'Net Worth', 'VAT', 'Gross Worth'

    Returns:
    --------
    validation_results : dict
        Comprehensive validation report with accuracy scores per domain
    """

    if domains is None:
        domains = [
            'vendor_normalized',
            'client_name',
            'seller_tax_id',
            'client_tax_id',
            'invoice_number',
            'invoice_date',
            'subtotal',
            'tax',
            'total',
            'line_items'
        ]
    elif isinstance(domains, str):
        domains = [domains]

    # Initialize results structure
    results = {
        'domains_validated': domains,
        'total_files': len(output_json),
        'files_matched': 0,
        'files_missing': [],
        'domain_results': {domain: {
            'matches': 0,
            'mismatches': 0,
            'missing_in_ground_truth': 0,
            'missing_in_output': 0,
            'accuracy': 0.0,
            'details': []
        } for domain in domains},
        'summary': {}
    }

    # Create invoice number index for batch_df for faster lookup
    batch_idx = {}
    for idx, row in batch_df.iterrows():
        # Extract invoice number from OCRed Text
        match = re.search(r'Invoice\s+no:\s*(\d+)', row["OCRed Text"])
        if match:
            # print("\n\n---------FOUND A MATCH\n")
            invoice_number = match.group(1)
            # print(invoice_number)
            batch_idx[invoice_number] = idx
            # if invoice_number == "91296589":
            #     print("FOUND SMTH")

            # Validate output_json file
    invoice_num = str(output_json['invoice_number'].iloc[0])
    # print("\n\n-------- TO FIND\n")
    # print(invoice_num)
    # print(type(invoice_num))

    # Find corresponding ground truth
    if invoice_num not in batch_idx.keys():  # it exists but it cannot be found
        results['files_missing'].append(invoice_num)
        # print(invoice_num)
        # print("IM NOT HERE RIGHT?")
        return []

    # results['files_matched'] += 1

    # Get the batch row using the invoice number lookup
    batch_row_idx = batch_idx[invoice_num]
    batch_row = batch_df.iloc[batch_row_idx]
    # print("\n\OCRED TEXT WITHIN VALIDATE FUNCTION")
    # print(batch_row['OCRed Text'])  # PROBLEM WITH THE OCRED NOT BEING CORRECT
    # exit(0)

    # Parse ground truth from OCRed Text, w/ same fields as json output file
    ground_truth = parse_ocred_text(batch_row['OCRed Text'])

    # Compare each domain
    for domain in domains:
        if domain not in ground_truth:
            continue

        gt_value = ground_truth[domain]
        ocr_value = output_json[domain].iloc[0]

        domain_result = results['domain_results'][domain]

        # Handle missing values
        if gt_value is None:
            domain_result['missing_in_ground_truth'] += 1
            domain_result['details'].append({
                'invoice_number': invoice_num,
                'status': 'missing_in_gt',
                'ground_truth': gt_value,
                'ocr_output': ocr_value
            })
            continue

        if pd.isna(ocr_value):
            domain_result['missing_in_output'] += 1
            domain_result['details'].append({
                'invoice_number': invoice_num,
                'status': 'missing_in_ocr',
                'ground_truth': gt_value,
                'ocr_output': None
            })
            continue

        # Determine field type and apply appropriate comparison
        is_numeric = domain in ['subtotal', 'tax',
                                'total', 'invoice_number']
        is_date = domain in ['Invoice Date']

        if is_date:
            # Extract date components and compare
            ocr_components = extract_date_components(ocr_value)
            gt_components = extract_date_components(gt_value)

            # For ambiguous dates (X/Y/YYYY where both X,Y <= 12), try both MM/DD and DD/MM interpretations
            is_match = False
            matched_gt_components = gt_components

            if ocr_components and gt_components:
                if gt_components == ocr_components:
                    is_match = True
                else:
                    # Try alternative interpretation for GT if it's ambiguous
                    if re.match(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', str(gt_value)):
                        parts = re.match(
                            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', str(gt_value)).groups()
                        a, b, year = int(parts[0]), int(
                            parts[1]), int(parts[2])
                        # Both <= 12: try swapped interpretation
                        if a <= 12 and b <= 12 and (a != b):
                            # Swap month and day
                            alt_gt_components = (year, b, a)
                            if alt_gt_components == ocr_components:
                                is_match = True
                                matched_gt_components = alt_gt_components

            score = 100 if is_match else 0

            domain_result['details'].append({
                'invoice_number': invoice_num,
                'status': 'match' if is_match else 'mismatch',
                'ground_truth': gt_value,
                'ground_truth_components': matched_gt_components,
                'ocr_output': ocr_value,
                'ocr_output_components': ocr_components,
                'score': score
            })

        elif is_numeric:
            # Strict numeric comparison
            # gt_value = float(gt_value)
            is_match, diff = strict_compare(
                gt_value, ocr_value, tolerance=tolerance)

            domain_result['details'].append({
                'invoice_number': invoice_num,
                'status': 'match' if is_match else 'mismatch',
                'ground_truth': gt_value,
                'ocr_output': ocr_value,
                'difference': diff,
                'score': 100 if is_match else 0
            })

        else:
            # Fuzzy string comparison
            score, is_match = fuzzy_compare(
                str(gt_value), str(ocr_value), threshold=fuzzy_threshold)

            domain_result['details'].append({
                'invoice_number': invoice_num,
                'status': 'match' if is_match else 'mismatch',
                'ground_truth': gt_value,
                'ocr_output': ocr_value,
                'similarity_score': score,
                'score': 100 if is_match else score
            })

        # Update counters
        if is_match:
            domain_result['matches'] += 1
        else:
            domain_result['mismatches'] += 1

    # Calculate accuracy for each domain
    for domain in domains:
        domain_result = results['domain_results'][domain]
        total_compared = domain_result['matches'] + domain_result['mismatches']

        if total_compared > 0:
            domain_result['accuracy'] = (
                domain_result['matches'] / total_compared) * 100

    # Calculate overall accuracy
    all_matches = sum(r['matches'] for r in results['domain_results'].values())
    all_comparisons = sum(r['matches'] + r['mismatches']
                          for r in results['domain_results'].values())

    results['summary'] = {
        'total_domains': len(domains),
        'total_comparisons': all_comparisons,
        'total_matches': all_matches,
        'overall_accuracy': (all_matches / all_comparisons * 100) if all_comparisons > 0 else 0.0
    }

    return results


print(
    "Validation function ready. Usage: validate_ocr_results(domains=['domain_name'])")
