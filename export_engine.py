"""
Export Engine for BillBrain AI.
Converts a list of InvoiceRecord objects to CSV or Excel bytes.
"""

import io
import csv

import openpyxl

from models import InvoiceRecord

COLUMNS = [
    "invoice_id",
    "filename",
    "vendor",
    "invoice_date",
    "items",
    "total_amount",
    "tax_amount",
    "due_date",
    "currency",
    "detected_language",
    "confidence_overall",
    "is_duplicate",
    "duplicate_of",
    "extracted_at",
]


def _record_to_row(record: InvoiceRecord) -> dict:
    """Map an InvoiceRecord to a flat dict with COLUMNS keys."""
    items_str = ", ".join(record.items) if record.items else ""
    return {
        "invoice_id": record.invoice_id if record.invoice_id is not None else "",
        "filename": record.filename if record.filename is not None else "",
        "vendor": record.vendor if record.vendor is not None else "",
        "invoice_date": str(record.invoice_date) if record.invoice_date is not None else "",
        "items": items_str,
        "total_amount": record.total_amount if record.total_amount is not None else "",
        "tax_amount": record.tax_amount if record.tax_amount is not None else "",
        "due_date": str(record.due_date) if record.due_date is not None else "",
        "currency": record.currency if record.currency is not None else "",
        "detected_language": record.detected_language if record.detected_language is not None else "",
        "confidence_overall": record.confidence.overall if record.confidence is not None else "",
        "is_duplicate": record.is_duplicate,
        "duplicate_of": record.duplicate_of if record.duplicate_of is not None else "",
        "extracted_at": str(record.extracted_at) if record.extracted_at is not None else "",
    }


def export_to_csv(records: list[InvoiceRecord]) -> bytes:
    """
    Returns UTF-8 encoded CSV bytes for all InvoiceRecord fields.
    Returns a valid empty CSV (header only) for an empty records list.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS)
    writer.writeheader()
    for record in records:
        writer.writerow(_record_to_row(record))
    return output.getvalue().encode("utf-8")


def export_to_excel(records: list[InvoiceRecord]) -> bytes:
    """
    Returns .xlsx bytes for all InvoiceRecord fields using openpyxl.
    Returns a valid empty Excel file (header only) for an empty records list.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoices"

    # Write header row
    ws.append(COLUMNS)

    # Write data rows
    for record in records:
        row = _record_to_row(record)
        ws.append([row[col] for col in COLUMNS])

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
