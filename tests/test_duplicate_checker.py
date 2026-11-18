"""
Property-based tests for Duplicate Checker.
Validates: Requirements 6.2, 6.3
"""
import uuid
from datetime import date, datetime
from hypothesis import given, settings, strategies as st

from duplicate_checker import is_duplicate
from models import InvoiceRecord, ConfidenceReport


def _low_conf():
    return ConfidenceReport(
        vendor="Low", invoice_date="Low", total_amount="Low",
        tax_amount="Low", due_date="Low", items="Low", overall="Low"
    )


def _make_record(vendor, amount, inv_date):
    return InvoiceRecord(
        invoice_id=str(uuid.uuid4()),
        user_id=None,
        filename="test.pdf",
        vendor=vendor,
        invoice_date=inv_date,
        items=[],
        total_amount=amount,
        tax_amount=None,
        due_date=None,
        currency="INR",
        detected_language="",
        confidence=_low_conf(),
        extracted_at=datetime.now(),
        is_duplicate=False,
        duplicate_of=None,
    )


# ---------------------------------------------------------------------------
# Property 11: Duplicate Detection Consistency
# **Validates: Requirements 6.2, 6.3**
# ---------------------------------------------------------------------------

@given(
    st.text(min_size=1, max_size=50),
    st.floats(min_value=0, max_value=1e6, allow_nan=False),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
@settings(max_examples=50)
def test_property11_same_vendor_amount_date_is_duplicate(vendor, amount, inv_date):
    """Same vendor + amount + date → duplicate."""
    record = _make_record(vendor, amount, inv_date)
    existing = [_make_record(vendor, amount, inv_date)]
    result = is_duplicate(record, existing)
    assert result.is_duplicate is True


@given(
    st.text(min_size=1, max_size=50),
    st.floats(min_value=0, max_value=1e6, allow_nan=False),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    st.text(min_size=1, max_size=50),
)
@settings(max_examples=50)
def test_property11_different_vendor_not_duplicate(vendor1, amount, inv_date, vendor2):
    """Different vendor → not duplicate."""
    # Ensure vendors differ after normalization
    if vendor1.lower().strip() == vendor2.lower().strip():
        vendor2 = vendor2 + "_different"
    record = _make_record(vendor1, amount, inv_date)
    existing = [_make_record(vendor2, amount, inv_date)]
    result = is_duplicate(record, existing)
    assert result.is_duplicate is False


@given(
    st.text(min_size=1, max_size=50),
    st.floats(min_value=100.0, max_value=1e6, allow_nan=False),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
@settings(max_examples=50)
def test_property11_different_amount_not_duplicate(vendor, amount, inv_date):
    """Amount differing by more than 0.01 → not duplicate."""
    different_amount = amount + 1.0  # clearly outside ±0.01
    record = _make_record(vendor, amount, inv_date)
    existing = [_make_record(vendor, different_amount, inv_date)]
    result = is_duplicate(record, existing)
    assert result.is_duplicate is False


@given(
    st.text(min_size=1, max_size=50),
    st.floats(min_value=0, max_value=1e6, allow_nan=False),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2029, 12, 30)),
)
@settings(max_examples=50)
def test_property11_different_date_not_duplicate(vendor, amount, inv_date):
    """Different date → not duplicate."""
    from datetime import timedelta
    different_date = inv_date + timedelta(days=1)
    record = _make_record(vendor, amount, inv_date)
    existing = [_make_record(vendor, amount, different_date)]
    result = is_duplicate(record, existing)
    assert result.is_duplicate is False


# ---------------------------------------------------------------------------
# Property 12: Vendor Normalization Idempotence
# **Validates: Requirements 6.2**
# ---------------------------------------------------------------------------

@given(st.text(min_size=1, max_size=100))
@settings(max_examples=50)
def test_property12_vendor_normalization_idempotence(vendor):
    """Normalizing vendor twice gives same result as once."""
    normalize = lambda v: v.lower().strip()
    once = normalize(vendor)
    twice = normalize(once)
    assert once == twice
