# OCR Invoice Validation Summary

## Overview
Validated OCR text extraction from invoices using ground truth data and model predictions on a sample of **30 randomly selected invoices**.

---

## Models & Approaches Used

### OCR Models
- **Tesseract** — Ground truth OCR text extraction
- **Regex Patterns** — Alternative text detection method when the LLM fails in some fields.


### Information Extraction
- **Gemini 2.5 Flash** — Structured information extraction model to convert the OCR text into a predefined JSON schema(required for the RAG) containing fields such as vendor, invoice number, metadata etc.


---

## Validation Methodology

### Comparison Per Domain
Validated the following fields across all 30 samples:

**Core Fields:**
- Client Name
- Seller Tax ID
- Client Tax ID
- Invoice Number
- Invoice Date
- Net Worth (subtotal)
- VAT (tax)
- Gross Worth (total)
- Vendor/Seller Name

### Matching Criteria
- **Text Fields:** Fuzzy matching with 90% similarity threshold (Character data)
- **Numeric Fields:** Strict matching with ±0.1 tolerance(Numbers)
- **Dates:** Component-based matching (year, month, day)

---

## Results

- **Total Samples:** 30 invoices
- **Domains Validated:** 9 key fields
- **Comparison Method:** Domain-by-domain accuracy measurement

### Extracted evaluation fields
### Validation Fields

The validation process focused on the following extracted invoice fields:

| Field | Description |
|---|---|
| `doc_type` | Document category, expected to be either `invoice` or `receipt` |
| `vendor` | Seller or issuer name |
| `invoice_number` | Unique invoice reference number |
| `invoice_date` | Invoice issue date |
| `currency` | Currency used in the invoice |
| `subtotal` | Net amount before tax |
| `tax` | VAT or tax amount |
| `total` | Final amount after tax |
| `status` | Payment status, such as `unknown`, `paid`, or `unpaid` |

Each field was evaluated independently to measure extraction accuracy at a more detailed level. This made it possible to identify which components of the extraction pipeline performed reliably and which fields required further improvement.

---

## Key Deliverables

1. ✓ Per-domain accuracy metrics
2. ✓ Mismatch identification and reporting
3. ✓ Ground truth verification pipeline
4. ✓ Scalable validation framework for future batches
