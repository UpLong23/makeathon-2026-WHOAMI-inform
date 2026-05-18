from typing import Any
from pydantic import BaseModel, Field


class InvoiceDocument(BaseModel):
    doc_id: str = Field(description="Unique document identifier")
    doc_type: str = "invoice"
    vendor: str | None = None
    vendor_normalized: str | None = None
    invoice_number: str | int | None = None
    invoice_date: str | None = None
    currency: str = "EUR"
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    status: str = "captured"
    line_items: list[dict[str, Any]] = []
    raw_text: str = ""
    client_name: str | None = None
    client_tax_id: str | None = None
    seller_tax_id: str | None = None
