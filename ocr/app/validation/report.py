
# ============================================================================
# REPORTING AND VISUALIZATION
# ============================================================================

def print_validation_report(validation_results, show_mismatches=True, show_all_details=False):
    """
    Print a formatted validation report.

    Parameters:
    -----------
    validation_results : dict
        Output from validate_ocr_results()
    show_mismatches : bool
        If True, show details of all mismatches
    show_all_details : bool
        If True, show all details including matches
    """

    results = validation_results

    print("\n" + "="*80)
    print("OCR VALIDATION REPORT")
    print("="*80)

    print(
        f"\nFiles Validated: {results['files_matched']} / {results['total_files']}")
    if results['files_missing']:
        print(
            f"Files Missing from Ground Truth: {len(results['files_missing'])}")

    print("\n" + "-"*80)
    print("OVERALL ACCURACY")
    print("-"*80)
    print(f"Total Comparisons: {results['summary']['total_comparisons']}")
    print(f"Total Matches: {results['summary']['total_matches']}")
    print(f"Overall Accuracy: {results['summary']['overall_accuracy']:.2f}%")

    print("\n" + "-"*80)
    print("DOMAIN-BY-DOMAIN ACCURACY")
    print("-"*80)

    # Create summary table
    domain_data = []
    for domain in results['domains_validated']:
        dr = results['domain_results'][domain]
        total = dr['matches'] + dr['mismatches']
        domain_data.append({
            'Domain': domain,
            'Matches': dr['matches'],
            'Mismatches': dr['mismatches'],
            'Missing GT': dr['missing_in_ground_truth'],
            'Missing OCR': dr['missing_in_output'],
            'Accuracy %': f"{dr['accuracy']:.2f}%"
        })

    domain_df = pd.DataFrame(domain_data)
    print(domain_df.to_string(index=False))

    # Show details if requested
    if show_mismatches or show_all_details:
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)

        for domain in results['domains_validated']:
            dr = results['domain_results'][domain]
            print(f"\n### {domain} ###")

            if show_all_details:
                # Show all details
                for detail in dr['details']:
                    print(f"  {detail['filename']}: {detail['status']}")
                    print(f"    GT:  {detail['ground_truth']}")
                    print(f"    OCR: {detail['ocr_output']}")
                    if 'similarity_score' in detail:
                        print(
                            f"    Similarity: {detail['similarity_score']:.0f}%")
                    if 'difference' in detail and detail['difference'] is not None:
                        print(f"    Difference: {detail['difference']}")
                    print()
            else:
                # Show only mismatches
                mismatches = [d for d in dr['details']
                              if d['status'] == 'mismatch']
                if mismatches:
                    print(f"  {len(mismatches)} mismatches:")
                    for detail in mismatches[:10]:  # Show first 10
                        print(f"    {detail['filename']}")
                        print(f"      GT:  {detail['ground_truth']}")
                        print(f"      OCR: {detail['ocr_output']}")
                        if 'similarity_score' in detail:
                            print(
                                f"      Similarity: {detail['similarity_score']:.0f}%")
                        if 'difference' in detail and detail['difference'] is not None:
                            print(f"      Difference: {detail['difference']}")
                    if len(mismatches) > 10:
                        print(f"    ... and {len(mismatches) - 10} more")
                else:
                    print(f"  ✓ All matches!")

    print("\n" + "="*80)


def get_mismatch_dataframe(validation_results, domain=None):
    """
    Extract mismatches as a pandas DataFrame for further analysis.

    Parameters:
    -----------
    validation_results : dict
        Output from validate_ocr_results()
    domain : str, optional
        Specific domain to extract. If None, returns all.

    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with all mismatches
    """

    rows = []

    if domain:
        domains_to_check = [domain]
    else:
        domains_to_check = validation_results['domains_validated']

    for dom in domains_to_check:
        for detail in validation_results['domain_results'][dom]['details']:
            if detail['status'] == 'mismatch':
                row = {
                    'Domain': dom,
                    'Filename': detail['filename'],
                    'Ground Truth': detail['ground_truth'],
                    'OCR Output': detail['ocr_output'],
                    'Status': detail['status']
                }

                if 'similarity_score' in detail:
                    row['Similarity %'] = detail['similarity_score']
                if 'difference' in detail:
                    row['Difference'] = detail['difference']

                rows.append(row)

    return pd.DataFrame(rows)


print("Reporting functions ready.")
print("\nUsage:")
print(
    "  results = validate_ocr_results(domains=['Seller Name', 'Invoice Date'])")
print("  print_validation_report(results)")
print("  mismatches_df = get_mismatch_dataframe(results)")
