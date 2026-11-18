"""
Property-based tests for Gemini Client.
Validates: Requirements 3.2, 3.3
"""
import sys
from unittest.mock import patch, MagicMock
from hypothesis import given, settings, strategies as st

# Patch st.secrets before gemini_client is imported (it reads secrets at module level)
_secrets_mock = MagicMock()
_secrets_mock.__getitem__ = MagicMock(return_value="fake-api-key")

with patch.dict(sys.modules, {"streamlit": MagicMock(secrets=_secrets_mock)}):
    import importlib
    import gemini_client as _gc_module
    # Ensure the module is loaded with the mock in place
    importlib.reload(_gc_module)

from models import InvoiceInput


def _make_invoice_input(content="fake content"):
    return InvoiceInput(
        filename="test.jpg",
        file_type="image",
        content=content,
        detected_language="",
    )


def _run_with_failing_api(invoice_input):
    """Run extract_structured_invoice with a mock that always raises."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Simulated API failure")

    with patch.object(_gc_module.genai, "GenerativeModel", return_value=mock_model):
        with patch.object(_gc_module.time, "sleep"):
            result = _gc_module.extract_structured_invoice(invoice_input)
    return result, mock_model


# ---------------------------------------------------------------------------
# Property 13: API Retry on Failure
# **Validates: Requirements 3.2, 3.3**
# ---------------------------------------------------------------------------

def test_property13_retry_on_failure_returns_none_after_3_attempts():
    """Mock API that always raises → extract_structured_invoice returns None after 3 attempts."""
    result, mock_model = _run_with_failing_api(_make_invoice_input())
    assert result is None


def test_property13_exactly_3_calls_made():
    """Verify exactly 3 calls are made to generate_content on repeated failure."""
    result, mock_model = _run_with_failing_api(_make_invoice_input())
    assert result is None
    assert mock_model.generate_content.call_count == 3


@given(st.text(min_size=1))
@settings(max_examples=20)
def test_property13_retry_always_returns_none_for_any_input(content):
    """For any invoice input, always-failing API returns None."""
    result, _ = _run_with_failing_api(_make_invoice_input(content))
    assert result is None
