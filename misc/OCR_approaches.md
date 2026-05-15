OCR on scanned documents means converting page images into machine-readable text. At a high level, there are four main approaches.

## 1. Traditional OCR engines

This is the classic approach: preprocess the scanned image, detect text regions, segment characters or words, and recognize the text.

Examples: **Tesseract**, ABBYY FineReader, Adobe OCR.

This works well when documents are clean, single-column, high-resolution, and mostly plain text. It is weaker when scans are skewed, noisy, handwritten, multi-column, table-heavy, or visually complex.

Typical pipeline:

```text
scanned page
→ grayscale / denoise / deskew / binarize
→ detect text lines
→ recognize characters or words
→ export text or searchable PDF
```

## 2. Deep-learning OCR

Modern OCR systems use neural networks for text detection and recognition. They are usually much better than traditional OCR on real-world scans.

Examples: **PaddleOCR**, EasyOCR, docTR, TrOCR.

A modern OCR model usually separates the task into:

```text
text detection: where is the text?
text recognition: what does the text say?
```

Transformer-based recognizers such as **TrOCR** are often strong for scanned or degraded text. PaddleOCR 3.0, for example, includes multilingual OCR, document parsing, and key-information extraction components, not just plain text recognition. ([arXiv][1])

## 3. Layout-aware OCR / document parsing

This is usually the best practical approach for scanned **documents**, not just scanned **text**.

Instead of only asking “what words are on the page?”, it also asks:

```text
What is the title?
What is a paragraph?
What is a table?
What is a figure?
What is a header/footer?
What is the reading order?
```

This matters a lot for reports, invoices, academic papers, contracts, financial statements, and PDFs with tables or columns.

A layout-aware system typically does:

```text
scanned page
→ image cleanup
→ layout detection
→ OCR inside each region
→ reading-order reconstruction
→ table extraction
→ structured output: Markdown / JSON / searchable PDF
```

PaddleOCR’s layout module, for example, detects regions such as text blocks, tables, figure titles, paragraph titles, and other document elements. ([PaddleOCR][2]) Recent layout models such as PP-DocLayout are designed specifically to detect structural elements like titles, text blocks, tables, and formulas across diverse document types. ([arXiv][3])

## 4. End-to-end vision-language/document models

These models try to read and understand the document directly from the image, sometimes without a separate OCR step.

Examples: **Donut**, Pix2Struct-style models, modern vision-language models, GPT-style vision models.

They can be very good for semantic extraction, such as:

```text
Extract the invoice number.
Find the total amount.
Summarize this page.
Extract all company names.
```

But for large-scale document digitization, they are not always the best first step because they can be slower, more expensive, harder to verify, and sometimes less reliable for exact verbatim text. They are excellent as a second layer for understanding after OCR.

---

# The best approach: layout-aware OCR pipeline

For scanned documents, the best general approach is **not plain OCR alone**. The best approach is a **layout-aware OCR pipeline**:

```text
1. Convert PDF pages to high-resolution images
2. Preprocess images
3. Detect page layout
4. Run OCR region by region
5. Reconstruct reading order
6. Preserve tables separately
7. Export clean text, Markdown, JSON, or searchable PDF
8. Optionally use an LLM for correction or semantic extraction
```

This is better because scanned documents are rarely just “text”. They contain structure. If you ignore the structure, the OCR output may be technically correct word-by-word but useless for analysis because paragraphs are mixed, columns are merged, tables are broken, and headers interrupt the text.

For example, a bad OCR result from a two-column report may read:

```text
The company reduced emissions Revenue increased by 12%
in 2023 across Scope 1 and Scope 2 compared to last year...
```

A layout-aware result would preserve the correct order:

```text
The company reduced emissions in 2023 across Scope 1 and Scope 2.

Revenue increased by 12% compared to last year.
```

For your type of work with company reports, PDFs, ESG text, and sentence extraction, I would think of the pipeline like this:

```text
Scanned company report
→ OCR + layout analysis
→ clean Markdown/text
→ sentence segmentation
→ filtering relevant sentences
→ classification / labeling
```

The OCR stage should aim to preserve **paragraphs, tables, headings, and page order**, not just extract raw text.

---

# Recommended practical setup

For most research or project work, I would use:

```text
PaddleOCR / PP-Structure
+ image preprocessing
+ Markdown or JSON output
+ optional LLM cleanup
```

Why this is a strong choice:

PaddleOCR is open-source, modern, multilingual, and includes both OCR and document-structure parsing. Its 3.0 version specifically targets OCR, hierarchical document parsing, and key-information extraction, which makes it more suitable for real scanned documents than plain OCR-only tools. ([arXiv][1])

A good practical architecture would be:

```text
PDF scan
→ pdf2image conversion at 300 DPI
→ deskew / denoise / contrast improvement
→ PaddleOCR text detection + recognition
→ PP-Structure layout parsing
→ export to Markdown
→ quality checks
```

Then, if needed:

```text
OCR text
→ LLM correction with original page image as reference
→ sentence extraction
→ downstream NLP/classification
```

The LLM should not replace OCR for everything. It is better used for cleanup, validation, formatting, and semantic extraction.

---

# When each method is appropriate

| Situation                            | Best method                                                                        |
| ------------------------------------ | ---------------------------------------------------------------------------------- |
| Clean scanned book pages             | Tesseract or PaddleOCR                                                             |
| Noisy scans                          | Deep-learning OCR                                                                  |
| Multi-column reports                 | Layout-aware OCR                                                                   |
| Tables and forms                     | Layout-aware OCR + table extraction                                                |
| Invoices/receipts                    | OCR + key-value extraction model                                                   |
| Need exact searchable PDF            | OCR engine with hidden text layer                                                  |
| Need semantic answers from documents | OCR + LLM                                                                          |
| Need high-volume production          | PaddleOCR, ABBYY, Google Document AI, Azure Document Intelligence, or AWS Textract |

---

# Important quality factors

OCR quality depends heavily on scan quality. The most important practical factors are:

```text
Resolution: ideally 300 DPI or higher
Skew: pages should be straightened
Contrast: text should be dark and background clean
Noise: remove speckles and shadows
Language: OCR must know the correct language
Layout: columns and tables need layout detection
Fonts: unusual fonts reduce accuracy
Handwriting: much harder than printed text
```

For scanned PDFs, creating a **searchable PDF** means keeping the original page image and adding an invisible OCR text layer on top. This is useful when you want the document to look identical but become searchable/copyable. ([Dpdf][4])

---

# My recommendation

For serious scanned-document processing, especially reports or research documents, use this:

```text
Best general method:
Layout-aware OCR using PaddleOCR / PP-Structure or a similar document-AI system.

Best enhancement:
Use an LLM after OCR for cleanup, validation, sentence extraction, and structured interpretation.

Avoid:
Relying only on plain OCR text extraction for complex reports.
```

For your project context, the most reliable workflow would be:

```text
1. OCR the scanned reports with a layout-aware tool.
2. Export structured text, preferably Markdown.
3. Manually inspect a sample of pages.
4. Fix recurring OCR problems with preprocessing.
5. Extract sentences only after the OCR text is clean.
6. Keep page references so every extracted sentence can be traced back to the original report.
```

[1]: https://arxiv.org/abs/2507.05595?utm_source=chatgpt.com "PaddleOCR 3.0 Technical Report"
[2]: https://www.paddleocr.ai/v3.3.1/en/version3.x/module_usage/layout_analysis.html?utm_source=chatgpt.com "Layout Analysis - PaddleOCR Documentation"
[3]: https://arxiv.org/abs/2503.17213?utm_source=chatgpt.com "PP-DocLayout: A Unified Document Layout Detection Model to Accelerate Large-Scale Data Construction"
[4]: https://www.dpdf.com/blog/how-to-ocr-scanned-pdf?utm_source=chatgpt.com "Make Scanned PDFs Searchable: An OCR Best‑Practice Guide (Accuracy & Size) - Dpdf"
