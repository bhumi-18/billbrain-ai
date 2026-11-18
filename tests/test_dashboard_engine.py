"""
Property-based tests for Dashboard Engine.
Validates: Requirements 9.1, 9.2
"""
import uuid
import datetime
from hypothesis import given, settings, strategies as st

from dashboard_engine import compute_dashboard
from models import InvoiceRecord, ConfidenceReport


def _low_conf():
    return ConfidenceReport(
        vendor="Low", invoice_date="Low", total_amount="Low",
        tax_amount="Low", due_date="Low", items="Low", overall="Low"
    )


def _make_record(vendor="ACME", amount=100.0, inv_date=None, due_date=None):
    return InvoiceRecord(
        invoice_id=str(uuid.uuid4()),
        user_id=None,
        filename="invoice.pdf",
        vendor=vendor,
        invoice_date=inv_date,
        items=[],
        total_amount=amount,
        tax_amount=None,
        due_date=due_date,
        currency="INR",
        detected_language="en",
        confidence=_low_conf(),
        extracted_at=datetime.datetime.now(),
        is_duplicate=False,
        duplicate_of=None,
    )


# ---------------------------------------------------------------------------
# Property 16: Total Correctness
# **Validates: Requirements 9.1**
# ---------------------------------------------------------------------------

@given(
    st.lists(
        st.floats(min_value=0, max_value=1e5, allow_nan=False),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=50)
def test_property16_total_spent_this_month(amounts):
    """total_spent_this_month equals sum of total_amount for current-month records."""
    today = datetime.date.today()
    current_month_date = today.replace(day=1)

    records = [_make_record(amount=a, inv_date=current_month_date) for a in amounts]
    summary = compute_dashboard(records)

    expected = sum(amounts)
    assert abs(summary.total_spent_this_month - expected) < 1e-6


@given(
    st.lists(
        st.floats(min_value=0, max_value=1e5, allow_nan=False),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=30)
def test_property16_past_month_records_excluded_from_total(amounts):
    """Records from a past month are NOT included in total_spent_this_month."""
    past_date = datetime.date(2020, 1, 1)
    records = [_make_record(amount=a, inv_date=past_date) for a in amounts]
    summary = compute_dashboard(records)
    assert summary.total_spent_this_month == 0.0


# ---------------------------------------------------------------------------
# Property 17: Overdue Filtering
# **Validates: Requirements 9.1**
# ---------------------------------------------------------------------------

@given(
    st.lists(
        st.dates(
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date(2023, 12, 31),  # all in the past
        ),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=50)
def test_property17_overdue_invoices_all_past_due_dates(due_dates):
    """overdue_invoices contains exactly records where due_date < today."""
    today = datetime.date.today()
    records = [_make_record(due_date=d) for d in due_dates]
    summary = compute_dashboard(records)

    # All provided dates are in the past, so all should be overdue
    expected_overdue_count = sum(1 for d in due_dates if d < today)
    assert len(summary.overdue_invoices) == expected_overdue_count


@given(
    st.lists(
        st.dates(
            min_value=datetime.date(2030, 1, 1),
            max_value=datetime.date(2035, 12, 31),  # all in the future
        ),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=30)
def test_property17_future_due_dates_not_overdue(due_dates):
    """Records with future due_date are NOT in overdue_invoices."""
    records = [_make_record(due_date=d) for d in due_dates]
    summary = compute_dashboard(records)
    assert len(summary.overdue_invoices) == 0


# ---------------------------------------------------------------------------
# Property 18: Top Vendor Correctness
# **Validates: Requirements 9.1**
# ---------------------------------------------------------------------------

@given(
    st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.floats(min_value=1.0, max_value=1e5, allow_nan=False),
        ),
        min_size=2,
        max_size=10,
    )
)
@settings(max_examples=50)
def test_property18_top_vendor_has_highest_spend(vendor_amounts):
    """top_vendor is the vendor with highest cumulative spend."""
    records = [_make_record(vendor=v, amount=a) for v, a in vendor_amounts]
    summary = compute_dashboard(records)

    # Compute expected top vendor manually
    from collections import defaultdict
    totals = defaultdict(float)
    for v, a in vendor_amounts:
        totals[v] += a

    expected_top = max(totals, key=lambda v: totals[v])
    assert summary.top_vendor == expected_top


def test_property18_empty_records_top_vendor_is_none():
    """Empty records → top_vendor is None."""
    summary = compute_dashboard([])
    assert summary.top_vendor is None
    assert summary.total_spent_this_month == 0.0
    assert summary.overdue_invoices == []
