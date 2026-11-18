"""
Example-based unit tests for error scenarios.
Covers: unsupported file type, malformed JSON fallback, empty export, empty dashboard.
"""
import csv
import io

import openpyxl

from file_handler import handle_uploaded_files
from extractor import parse_extraction_result
from export_engine import export_to_csv, export_to_excel
from dashboard_engine import compute_dashboard


class MockFile:
    def __init__(self, name, mime_type, data=b"fake data"):
        self.name = name
        self.type = mime_type
        self._data = data

    def getvalue(self):
        return self._data


# ---------------------------------------------------------------------------
# Unsupported file type warning
# ---------------------------------------------------------------------------

def test_unsupported_file_type_produces_error_record():
    """Uploading a .txt file produces file_type='error', not an exception."""
    f = MockFile("document.txt", "text/plain", b"some text content")
    results = handle_uploaded_files([f])
    assert len(results) == 1
    assert results[0].file_type == "error"
    assert results[0].filename == "document.txt"


def test_unsupported_file_type_content_is_string():
    """Error record content is a descriptive string, not None."""
    f = MockFile("archive.zip", "application/zip", b"PK\x03\x04")
    results = handle_uploaded_files([f])
    assert results[0].file_type == "error"
    assert isinstance(results[0].content, str)


# ---------------------------------------------------------------------------
# Malformed JSON fallback
# ---------------------------------------------------------------------------

def test_malformed_json_returns_valid_invoice_record():
    """Malformed JSON input returns a valid InvoiceRecord, no exception raised."""
    malformed = '{"vendor": "ACME", "total_amount": INVALID_JSON'
    result = parse_extraction_result(malformed)
    assert result is not None
    # Should have a UUID
    assert result.invoice_id is not None
    assert len(result.invoice_id) > 0


def test_malformed_json_no_exception():
    """parse_extraction_result never raises, even for completely broken input."""
    inputs = [
        "",
        "not json at all",
        "{broken: json}",
        "[]",
        "   ",
        "\x00\x01\x02",
        "null",       # valid JSON but not a dict — should fall back gracefully
        "Infinity",   # parsed by json as float, not a dict
        "true",       # valid JSON bool, not a dict
        "42",         # valid JSON number, not a dict
    ]
    for bad_input in inputs:
        result = parse_extraction_result(bad_input)
        assert result is not None, f"Got None for input: {bad_input!r}"


def test_malformed_json_fallback_confidence_low():
    """Completely unparseable input → confidence.overall == 'Low'."""
    result = parse_extraction_result("!!! NOT JSON !!!")
    assert result.confidence.overall == "Low"


# ---------------------------------------------------------------------------
# Empty export
# ---------------------------------------------------------------------------

def test_empty_csv_export_no_exception():
    """export_to_csv([]) returns valid CSV bytes with headers, no exception."""
    result = export_to_csv([])
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_empty_csv_export_has_headers():
    """Empty CSV export contains all expected column headers."""
    result = export_to_csv([])
    reader = csv.DictReader(io.StringIO(result.decode("utf-8")))
    assert reader.fieldnames is not None
    assert len(reader.fieldnames) == 14
    rows = list(reader)
    assert len(rows) == 0


def test_empty_excel_export_no_exception():
    """export_to_excel([]) returns valid .xlsx bytes, no exception."""
    result = export_to_excel([])
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_empty_excel_export_has_headers():
    """Empty Excel export contains all expected column headers."""
    result = export_to_excel([])
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    assert len(headers) == 14
    # Only header row, no data rows
    assert ws.max_row == 1


# ---------------------------------------------------------------------------
# Empty dashboard
# ---------------------------------------------------------------------------

def test_empty_dashboard_top_vendor_none():
    """compute_dashboard([]) → top_vendor=None."""
    summary = compute_dashboard([])
    assert summary.top_vendor is None


def test_empty_dashboard_total_zero():
    """compute_dashboard([]) → total_spent_this_month=0.0."""
    summary = compute_dashboard([])
    assert summary.total_spent_this_month == 0.0


def test_empty_dashboard_overdue_empty():
    """compute_dashboard([]) → overdue_invoices=[]."""
    summary = compute_dashboard([])
    assert summary.overdue_invoices == []


def test_empty_dashboard_no_exception():
    """compute_dashboard([]) completes without raising any exception."""
    summary = compute_dashboard([])
    assert summary is not None
