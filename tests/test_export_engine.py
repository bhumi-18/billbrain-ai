"""
Property-based tests for Export Engine.
Validates: Requirements 7.1, 7.2, 7.3
"""
import csv
import io
import uuid
from datetime import date, datetime
from hypothesis import given, settings, strategies as st

import openpyxl

from export_engine import export_to_csv, export_to_excel, COLUMNS
from models import InvoiceRecord, ConfidenceReport


def _low_conf():
    return ConfidenceReport(
        vendor="Low", invoice_date="Low", total_amount="Low",
        tax_amount="Low", due_date="Low", items="Low", overall="Low"
    )


def _make_record(vendor="ACME", amount=100.0, inv_date=None, items=None):
    return InvoiceRecord(
        invoice_id=str(uuid.uuid4()),
        user_id=None,
        filename="invoice.pdf",
        vendor=vendor,
        invoice_date=inv_date or date(2024, 1, 15),
        items=items or ["Item A"],
        total_amount=amount,
        tax_amount=18.0,
        due_date=date(2024, 2, 15),
        currency="INR",
        detected_language="en",
        confidence=_low_conf(),
        extracted_at=datetime(2024, 1, 15, 10, 0, 0),
        is_duplicate=False,
        duplicate_of=None,
    )


# ---------------------------------------------------------------------------
# Property 14: CSV Round-trip
# **Validates: Requirements 7.1**
# ---------------------------------------------------------------------------

@given(
    st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))),
    st.floats(min_value=0, max_value=1e6, allow_nan=False),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))), min_size=1, max_size=5),
)
@settings(max_examples=50)
def test_property14_csv_roundtrip(vendor, amount, inv_date, items):
    """Export records to CSV, re-parse CSV, verify vendor/amount/date fields match."""
    record = _make_record(vendor=vendor, amount=amount, inv_date=inv_date, items=items)
    csv_bytes = export_to_csv([record])

    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
    rows = list(reader)
    assert len(rows) == 1

    row = rows[0]
    assert row["vendor"] == (vendor if vendor is not None else "")
    assert row["invoice_date"] == str(inv_date)
    # Amount comparison: parse back as float
    assert abs(float(row["total_amount"]) - amount) < 1e-6


# ---------------------------------------------------------------------------
# Property 15: Export Column Completeness
# **Validates: Requirements 7.1, 7.2**
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
    "invoice_id", "filename", "vendor", "invoice_date", "items",
    "total_amount", "tax_amount", "due_date", "currency", "detected_language",
    "confidence_overall", "is_duplicate", "duplicate_of", "extracted_at",
]


@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=30)
def test_property15_csv_column_completeness(n):
    """Exported CSV always contains all 14 expected columns."""
    records = [_make_record(vendor=f"Vendor {i}", amount=float(i * 100)) for i in range(n)]
    csv_bytes = export_to_csv(records)
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
    assert reader.fieldnames is not None
    for col in EXPECTED_COLUMNS:
        assert col in reader.fieldnames, f"Missing column: {col}"


@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=30)
def test_property15_excel_column_completeness(n):
    """Exported Excel always contains all 14 expected columns."""
    records = [_make_record(vendor=f"Vendor {i}", amount=float(i * 100)) for i in range(n)]
    excel_bytes = export_to_excel(records)
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    for col in EXPECTED_COLUMNS:
        assert col in headers, f"Missing column in Excel: {col}"
