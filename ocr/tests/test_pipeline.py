import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from app.schemas import InvoiceDocument
from app.transform import extract_fields, structure_for_llm, regex_extraction_fallback
from app.pipeline import _normalize_to_document


class TestJsonParsing:
    def test_normalize_expected_fields(self):
        fields = {
            "Seller Name": "Acme Corp",
            "Seller Tax ID": "123-45-6789",
            "Client Name": "Beta LLC",
            "Client Tax ID": "987-65-4321",
            "Invoice Number": "INV-001",
            "Invoice Date": "2024-01-15",
            "Net Worth": 1000.0,
            "VAT": 200.0,
            "Gross Worth": 1200.0,
        }
        doc = _normalize_to_document(fields, "some raw text", idx=1)
        assert doc.doc_id == "inv_001"
        assert doc.vendor == "Acme Corp"
        assert doc.vendor_normalized == "acme corp"
        assert doc.subtotal == 1000.0
        assert doc.tax == 200.0
        assert doc.total == 1200.0
        assert doc.status == "captured"

    def test_normalize_missing_fields(self):
        fields = {k: None for k in [
            "Seller Name", "Seller Tax ID", "Client Name", "Client Tax ID",
            "Invoice Number", "Invoice Date", "Net Worth", "VAT", "Gross Worth",
        ]}
        doc = _normalize_to_document(fields, "", idx=2)
        assert doc.doc_id == "inv_002"
        assert doc.vendor is None
        assert doc.subtotal is None

    def test_normalize_safe_float_edge_cases(self):
        fields = {
            "Seller Name": "X",
            "Seller Tax ID": None,
            "Client Name": None,
            "Client Tax ID": None,
            "Invoice Number": None,
            "Invoice Date": None,
            "Net Worth": "1,612.50",
            "VAT": "not-a-number",
            "Gross Worth": None,
        }
        doc = _normalize_to_document(fields, "")
        assert doc.subtotal is None
        assert doc.tax is None
        assert doc.total is None


class TestRegexFallback:
    def test_regex_fallback_empty(self):
        result = regex_extraction_fallback("")
        for field in [
            "Seller Name", "Seller Tax ID", "Client Name", "Client Tax ID",
            "Invoice Number", "Invoice Date",
        ]:
            assert result[field] is None
        assert result["Net Worth"] is None

    def test_regex_fallback_malformed(self):
        result = regex_extraction_fallback("no blocks here\njust garbage")
        for v in result.values():
            assert v is None


class TestStructureForLLM:
    def test_empty_text(self):
        assert structure_for_llm("") == ""

    def test_no_tabs(self):
        text = "Invoice no: 123\nDate: 2024-01-01"
        result = structure_for_llm(text)
        assert "=== INVOICE DETAILS ===" in result
        assert "Invoice no: 123" in result
        assert "=== SELLER BLOCK ===" not in result

    def test_tab_separated(self):
        text = "LeftColumn\tRightColumn\nSomeData\tMoreData"
        result = structure_for_llm(text)
        assert "=== SELLER BLOCK ===" in result
        assert "=== CLIENT BLOCK ===" in result
        assert "LeftColumn" in result
        assert "RightColumn" in result


class TestExtractFields:
    def test_llm_malformed_json_returns_regex(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "not json at all"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        text = "Invoice no: ABC-123\nDate: 01/15/2024"
        structured = structure_for_llm(text)
        result = extract_fields(structured, mock_client)
        assert isinstance(result, dict)


class TestFailureHandling:
    def test_invalid_image_path(self):
        from app.ocr import run_ocr
        with pytest.raises(ValueError, match="Could not read image"):
            run_ocr("/nonexistent/path/image.jpg")

    def test_malformed_model_output_parsing(self):
        malformed = '{"Seller Name": "X"'
        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed)


@pytest.fixture
def mock_groq():
    with patch("app.transform.Groq") as mock:
        yield mock


class TestEndToEndPipelineSmoke:
    def test_pipeline_with_mocked_deps(self, tmp_path: Path):
        from app.pipeline import process_image

        img_path = tmp_path / "test_input.jpg"
        output_path = tmp_path / "test_output.json"

        import cv2
        import numpy as np
        dummy_img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        cv2.imwrite(str(img_path), dummy_img)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "Seller Name": "Test Vendor",
            "Seller Tax ID": "12-3456789",
            "Client Name": "Test Client",
            "Client Tax ID": "98-7654321",
            "Invoice Number": "INV-99",
            "Invoice Date": "2024-06-15",
            "Net Worth": 500.0,
            "VAT": 50.0,
            "Gross Worth": 550.0,
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        doc = process_image(str(img_path), mock_client, currency="USD")
        assert doc.doc_id == "inv_001"
        assert doc.vendor == "Test Vendor"
        assert doc.currency == "USD"
        assert doc.subtotal == 500.0
        assert doc.tax == 50.0
        assert doc.total == 550.0

        with open(str(output_path), "w") as f:
            json.dump(doc.model_dump(), f, indent=2)

        with open(str(output_path)) as f:
            saved = json.load(f)
        assert saved["vendor"] == "Test Vendor"
