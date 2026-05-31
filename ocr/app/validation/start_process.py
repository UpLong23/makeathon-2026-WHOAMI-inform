from validate import validate_ocr_results
import pandas as pd
from report import print_validation_report

# ============================================================================
# PARAMETERS AND DATASET LOAD
# ============================================================================
batch1_df = pd.read_csv(
    r"/Users/grigoriostsakalis/.cache/kagglehub/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr/versions/3/batch_1/batch_1/batch1_1.csv")
output_json = pd.read_json(
    r"/Users/grigoriostsakalis/Desktop/UniAI/makeathon-2026-WHOAMI-inform/ocr/app/app_output.json")
# print(batch1_df['OCRed Text'].head(3))
# ============================================================================
# ============================================================================

print("Starting full validation on all domains...")
print("This may take a moment...\n")

# print(batch1_df.head(3)["OCRed Text"].iloc["Invoice no:"])
# exit(0)

# ground_truth_df = batch1_df["OCRed Text"]
# print(type(ground_truth_df))
# print("\n\n\n\n")
# print(type(output_json))

# Run validation on all domains
full_results = validate_ocr_results(
    batch_df=batch1_df, output_json=output_json)

# # Print report
# print_validation_report(
#     full_results, show_mismatches=True, show_all_details=False)
