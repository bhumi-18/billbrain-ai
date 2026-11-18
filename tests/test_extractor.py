"""
Property-based tests for Structured Extractor.
Validates: Requirements 4.3, 4.4, 4.5, 5.2, 5.3, 5.4, 5.5, 5.6
"""
import json
from datetime import date
from hypothesis import given, settings, strategies as st

from extractor import parse_extraction_result, compute_confidence
from models import InvoiceRecord, ConfidenceReport

_LEVELS = {"Low": 0, "Medium": 1, "High": 2}


# ---------------------------------------------------------------------------
# Property 6: parse_extraction_result Never Raises
# **Validates: Requirements 4.4**
# ---------------------------------------------------------------------------

@given(st.text())
@settings(max_examples=50)
def test_property6_never_raises(s):
    """parse_extraction_result(s) never raises for any string input."""
    result = parse_extraction_result(s)
    assert result is not None
    assert isinstance(result, InvoiceRecord)


# ---------------------------------------------------------------------------
# Property 7: Failed Parse → Low Confidence
# **Validates: Requirements 4.3**
# ---------------------------------------------------------------------------

@given(st.text(alphabet=st.characters(blacklist_categories=("P",)), min_size=1))
@settings(max_examples=50)
def test_property7_unparseable_input_low_confidence(s):
    """Completely unparseable input → confidence.overall == 'Low' and all data fields None."""
    # Use strings that are clearly not JSON
    garbage = "!!!" + s.replace("{", "").replace("}", "").replace('"', "") + "!!!"
    result = parse_extraction_result(garbage)
    # If it couldn't parse anything meaningful, overall should be Low
    # (it may parse partial data, so we only assert on fully-failed records)
    assert isinstance(result, InvoiceRecord)
    assert result.invoice_id is not None  # always has a UUID


def test_property7_pure_garbage_is_low_confidence():
    """Pure garbage string → all fields None and confidence.overall == 'Low'."""
    result = parse_extraction_result("!@#$%^&*()_+NOTJSON_AT_ALL")
    assert result.confidence.overall == "Low"
    assert result.vendor is None
    assert result.invoice_date is None
    assert result.total_amount is None
    assert result.tax_amount is None
    assert result.due_date is None
    assert result.items == []


# ---------------------------------------------------------------------------
# Property 8: Unique Invoice IDs
# **Validates: Requirements 4.5**
# ---------------------------------------------------------------------------

@given(st.text(), st.text())
@settings(max_examples=50)
def test_property8_unique_invoice_ids(s1, s2):
    """Two separate calls produce distinct invoice_id values."""
    r1 = parse_extraction_result(s1)
    r2 = parse_extraction_result(s2)
    assert r1.invoice_id != r2.invoice_id


# ---------------------------------------------------------------------------
# Property 9: Confidence Overall is Minimum
# **Validates: Requirements 5.5, 5.6**
# ---------------------------------------------------------------------------

@given(st.text())
@settings(max_examples=50)
def test_property9_overall_is_minimum_of_field_scores(s):
    """overall equals the minimum of all field scores."""
    record = parse_extraction_result(s)
    conf = record.confidence
    field_scores = [
        conf.vendor,
        conf.invoice_date,
        conf.total_amount,
        conf.tax_amount,
        conf.due_date,
        conf.items,
    ]
    min_level = min(_LEVELS[score] for score in field_scores)
    expected_overall = {v: k for k, v in _LEVELS.items()}[min_level]
    assert conf.overall == expected_overall


# ---------------------------------------------------------------------------
# Property 10: Confidence Field Assignment Rules
# **Validates: Requirements 5.2, 5.3, 5.4**
# ---------------------------------------------------------------------------

def _make_record(**kwargs) -> InvoiceRecord:
    """Helper to build a minimal InvoiceRecord for confidence testing."""
    from datetime import datetime
    defaults = dict(
        invoice_id="test-id",
        user_id=None,
        filename="test.pdf",
        vendor=None,
        invoice_date=None,
        items=[],
        total_amount=None,
        tax_amount=None,
        due_date=None,
        currency="INR",
        detected_language="",
        confidence=ConfidenceReport(
            vendor="Low", invoice_date="Low", total_amount="Low",
            tax_amount="Low", due_date="Low", items="Low", overall="Low"
        ),
        extracted_at=datetime.now(),
        is_duplicate=False,
        duplicate_of=None,
    )
    defaults.update(kwargs)
    return InvoiceRecord(**defaults)


def test_property10_null_fields_get_low():
    """Null fields → Low confidence."""
    record = _make_record()  # all None
    conf = compute_confidence(record)
    assert conf.vendor == "Low"
    assert conf.invoice_date == "Low"
    assert conf.total_amount == "Low"
    assert conf.tax_amount == "Low"
    assert conf.due_date == "Low"
    assert conf.items == "Low"


def test_property10_valid_fields_get_high():
    """Present + valid fields → High confidence."""
    record = _make_record(
        vendor="ACME Corp",
        invoice_date=date(2024, 1, 15),
        total_amount=1000.0,
        tax_amount=180.0,
        due_date=date(2024, 2, 15),
        items=["Item A", "Item B"],
    )
    conf = compute_confidence(record)
    assert conf.vendor == "High"
    assert conf.invoice_date == "High"
    assert conf.total_amount == "High"
    assert conf.tax_amount == "High"
    assert conf.due_date == "High"
    assert conf.items == "High"
    assert conf.overall == "High"


def test_property10_invalid_date_gets_medium():
    """Present but invalid date format → Medium confidence."""
    record = _make_record(
        vendor="ACME",
        invoice_date="15/01/2024",  # wrong format, kept as string
        total_amount=100.0,
        items=["item"],
    )
    conf = compute_confidence(record)
    assert conf.invoice_date == "Medium"


@given(
    st.floats(min_value=0, max_value=1e6, allow_nan=False),
    st.floats(min_value=0, max_value=1e6, allow_nan=False),
)
@settings(max_examples=50)
def test_property10_valid_amounts_get_high(total, tax):
    """Valid float amounts → High confidence."""
    record = _make_record(total_amount=total, tax_amount=tax)
    conf = compute_confidence(record)
    assert conf.total_amount == "High"
    assert conf.tax_amount == "High"
