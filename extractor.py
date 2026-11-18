import json
import re
import uuid
from datetime import datetime, date

from models import InvoiceRecord, ConfidenceReport

# Regex to match YYYY-MM-DD date format
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _make_confidence(
    vendor=None,
    invoice_date=None,
    total_amount=None,
    tax_amount=None,
    due_date=None,
    items=None,
    overall="Low",
) -> ConfidenceReport:
    return ConfidenceReport(
        vendor=vendor or "Low",
        invoice_date=invoice_date or "Low",
        total_amount=total_amount or "Low",
        tax_amount=tax_amount or "Low",
        due_date=due_date or "Low",
        items=items or "Low",
        overall=overall,
    )


def _low_confidence() -> ConfidenceReport:
    return _make_confidence(overall="Low")


def _build_record(data: dict, filename: str = "") -> InvoiceRecord:
    """Build an InvoiceRecord from a parsed dict, applying defaults."""
    # Parse invoice_date — keep raw string for confidence scoring if parse fails
    invoice_date = None
    raw_date = data.get("invoice_date")
    if raw_date:
        try:
            invoice_date = date.fromisoformat(str(raw_date))
        except (ValueError, TypeError):
            # Store raw string so compute_confidence can assign "Medium"
            invoice_date = str(raw_date)

    # Parse due_date — same strategy
    due_date = None
    raw_due = data.get("due_date")
    if raw_due:
        try:
            due_date = date.fromisoformat(str(raw_due))
        except (ValueError, TypeError):
            due_date = str(raw_due)

    # Parse total_amount — keep raw value for confidence scoring if parse fails
    total_amount = None
    raw_total = data.get("total_amount")
    if raw_total is not None:
        try:
            total_amount = float(raw_total)
        except (ValueError, TypeError):
            total_amount = str(raw_total)  # present but unparseable → Medium

    # Parse tax_amount — same strategy
    tax_amount = None
    raw_tax = data.get("tax_amount")
    if raw_tax is not None:
        try:
            tax_amount = float(raw_tax)
        except (ValueError, TypeError):
            tax_amount = str(raw_tax)

    items = data.get("items") or []
    if not isinstance(items, list):
        items = []

    record = InvoiceRecord(
        invoice_id=str(uuid.uuid4()),
        user_id=None,
        filename=filename,
        vendor=data.get("vendor") or None,
        invoice_date=invoice_date,  # type: ignore[arg-type]
        items=items,
        total_amount=total_amount,  # type: ignore[arg-type]
        tax_amount=tax_amount,  # type: ignore[arg-type]
        due_date=due_date,  # type: ignore[arg-type]
        currency=data.get("currency") or "INR",
        detected_language=data.get("detected_language") or "",
        confidence=_low_confidence(),  # will be replaced by compute_confidence
        extracted_at=datetime.now(),
        is_duplicate=False,
        duplicate_of=None,
    )
    record.confidence = compute_confidence(record)

    # Fallback language detection if Gemini didn't provide it
    if not record.detected_language:
        try:
            from langdetect import detect
            text_to_detect = " ".join(record.items) or record.vendor or ""
            if text_to_detect.strip():
                record.detected_language = detect(text_to_detect)
        except Exception:
            pass  # langdetect is optional fallback

    return record


def parse_extraction_result(raw: str) -> InvoiceRecord:
    """Parses Gemini JSON output into InvoiceRecord. Never raises."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return _build_record(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Regex fallback: find first {...} block in the string
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if isinstance(data, dict):
                return _build_record(data)
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        pass

    # Both failed — return a fully-failed record
    return _failed_record()


def _failed_record(filename: str = "") -> InvoiceRecord:
    return InvoiceRecord(
        invoice_id=str(uuid.uuid4()),
        user_id=None,
        filename=filename,
        vendor=None,
        invoice_date=None,
        items=[],
        total_amount=None,
        tax_amount=None,
        due_date=None,
        currency="INR",
        detected_language="",
        confidence=_low_confidence(),
        extracted_at=datetime.now(),
        is_duplicate=False,
        duplicate_of=None,
    )


def create_failed_record(filename: str) -> InvoiceRecord:
    """Returns a failed InvoiceRecord (all data fields None, confidence Low)."""
    return _failed_record(filename=filename)


def compute_confidence(record: InvoiceRecord) -> ConfidenceReport:
    """
    Returns High/Medium/Low confidence per field
    based on field presence and format validity.
    overall = minimum confidence across all fields.
    """
    _LEVELS = {"Low": 0, "Medium": 1, "High": 2}

    def _vendor_conf(v) -> str:
        if v and isinstance(v, str) and v.strip():
            return "High"
        return "Low"

    def _date_conf(v) -> str:
        if v is None:
            return "Low"
        # Already a date object — was successfully parsed → High
        if isinstance(v, date):
            return "High"
        # Raw string kept because fromisoformat failed → present but wrong format
        s = str(v).strip()
        if not s:
            return "Low"
        # If it happens to match YYYY-MM-DD it's High, otherwise Medium
        if _DATE_RE.match(s):
            return "High"
        return "Medium"

    def _amount_conf(v) -> str:
        if v is None:
            return "Low"
        if isinstance(v, (int, float)):
            return "High"
        # Raw string kept because float() failed → present but unparseable
        try:
            float(str(v))
            return "High"
        except (ValueError, TypeError):
            return "Medium"

    def _items_conf(v) -> str:
        if isinstance(v, list) and len(v) > 0:
            return "High"
        return "Low"

    scores = {
        "vendor": _vendor_conf(record.vendor),
        "invoice_date": _date_conf(record.invoice_date),
        "total_amount": _amount_conf(record.total_amount),
        "tax_amount": _amount_conf(record.tax_amount),
        "due_date": _date_conf(record.due_date),
        "items": _items_conf(record.items),
    }

    min_level = min(_LEVELS[s] for s in scores.values())
    level_names = {v: k for k, v in _LEVELS.items()}
    overall = level_names[min_level]

    return ConfidenceReport(
        vendor=scores["vendor"],
        invoice_date=scores["invoice_date"],
        total_amount=scores["total_amount"],
        tax_amount=scores["tax_amount"],
        due_date=scores["due_date"],
        items=scores["items"],
        overall=overall,
    )
