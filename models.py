from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class InvoiceInput:
    filename: str
    file_type: str          # "image" | "pdf" | "error"
    content: dict | str     # Gemini image part dict OR extracted PDF text
    detected_language: str  # "en" | "hi" | "ta" | "mr" | auto-detected


@dataclass
class ConfidenceReport:
    vendor: str             # "High" | "Medium" | "Low"
    invoice_date: str
    total_amount: str
    tax_amount: str
    due_date: str
    items: str
    overall: str            # Lowest confidence across all fields


@dataclass
class InvoiceRecord:
    invoice_id: str         # UUID, generated on creation
    user_id: str | None     # None for unauthenticated sessions
    filename: str
    vendor: str | None
    invoice_date: date | None
    items: list[str]        # Line item descriptions
    total_amount: float | None
    tax_amount: float | None
    due_date: date | None
    currency: str           # Default "INR"
    detected_language: str
    confidence: ConfidenceReport
    extracted_at: datetime
    is_duplicate: bool
    duplicate_of: str | None  # invoice_id of matching record


@dataclass
class DuplicateResult:
    is_duplicate: bool
    matching_invoice_id: str | None
    matching_filename: str | None


@dataclass
class DashboardSummary:
    total_spent_this_month: float
    top_vendor: str | None
    top_vendor_amount: float
    overdue_invoices: list[InvoiceRecord]
    invoice_count_by_month: dict[str, int]  # "YYYY-MM" -> count
