from models import InvoiceRecord, DuplicateResult


def is_duplicate(record: InvoiceRecord, existing: list[InvoiceRecord]) -> DuplicateResult:
    """
    Returns DuplicateResult with is_duplicate flag
    and matching record reference if found.
    Matching criteria: vendor + amount + date.
    """
    for candidate in existing:
        # Vendor match: normalize both sides
        if record.vendor is None or candidate.vendor is None:
            continue
        if record.vendor.lower().strip() != candidate.vendor.lower().strip():
            continue

        # Amount match: within ±0.01
        if record.total_amount is None or candidate.total_amount is None:
            continue
        if abs(record.total_amount - candidate.total_amount) > 0.01:
            continue

        # Date match: exact equality
        if record.invoice_date is None or candidate.invoice_date is None:
            continue
        if record.invoice_date != candidate.invoice_date:
            continue

        # All three criteria met
        return DuplicateResult(
            is_duplicate=True,
            matching_invoice_id=candidate.invoice_id,
            matching_filename=candidate.filename,
        )

    return DuplicateResult(is_duplicate=False, matching_invoice_id=None, matching_filename=None)
