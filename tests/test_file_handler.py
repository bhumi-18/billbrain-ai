"""
Property-based tests for File Handler.
Validates: Requirements 1.2, 1.3, 1.6, 1.7, 2.3
"""
import io
import pytest
from hypothesis import given, settings, strategies as st

from file_handler import handle_uploaded_files, FileLimitExceededError

ACCEPTED_MIME_TYPES = ["image/jpeg", "image/png", "application/pdf"]
UNSUPPORTED_MIME_TYPES = ["text/plain", "application/zip", "video/mp4", "image/gif"]


class MockFile:
    def __init__(self, name, mime_type, data=b"fake data"):
        self.name = name
        self.type = mime_type
        self._data = data

    def getvalue(self):
        return self._data


def make_mock_image(name="test.jpg", mime_type="image/jpeg"):
    return MockFile(name, mime_type, b"fake image data")


def make_mock_pdf(name="test.pdf"):
    """Create a minimal valid PDF using a seekable BytesIO-backed mock."""
    import io as _io
    pdf_bytes = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""

    class SeekableMockFile:
        def __init__(self):
            self.name = name
            self.type = "application/pdf"
            self._buf = _io.BytesIO(pdf_bytes)

        def getvalue(self):
            return pdf_bytes

        def read(self, *args):
            return self._buf.read(*args)

        def seek(self, *args):
            return self._buf.seek(*args)

        def tell(self):
            return self._buf.tell()

    return SeekableMockFile()


# ---------------------------------------------------------------------------
# Property 1: Batch Size Invariant
# **Validates: Requirements 1.6, 7.2**
# ---------------------------------------------------------------------------

@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=50)
def test_property1_batch_size_invariant(n):
    """len(handle_uploaded_files(files)) == len(files) for 1–20 valid image files."""
    files = [make_mock_image(f"file_{i}.jpg") for i in range(n)]
    result = handle_uploaded_files(files)
    assert len(result) == n


# ---------------------------------------------------------------------------
# Property 2: File Limit Rejection
# **Validates: Requirements 1.2**
# ---------------------------------------------------------------------------

@given(st.integers(min_value=21, max_value=50))
@settings(max_examples=30)
def test_property2_file_limit_rejection(n):
    """handle_uploaded_files raises FileLimitExceededError for >20 files."""
    files = [make_mock_image(f"file_{i}.jpg") for i in range(n)]
    with pytest.raises(FileLimitExceededError):
        handle_uploaded_files(files)


# ---------------------------------------------------------------------------
# Property 3: File Type Acceptance
# **Validates: Requirements 1.3**
# ---------------------------------------------------------------------------

@given(st.sampled_from(ACCEPTED_MIME_TYPES))
@settings(max_examples=50)
def test_property3_accepted_mime_types_produce_non_error(mime_type):
    """Accepted MIME types produce non-error InvoiceInput."""
    if mime_type == "application/pdf":
        f = make_mock_pdf()
    else:
        f = MockFile("test_file", mime_type, b"fake image bytes")
    result = handle_uploaded_files([f])
    assert len(result) == 1
    assert result[0].file_type != "error"


@given(st.sampled_from(UNSUPPORTED_MIME_TYPES))
@settings(max_examples=50)
def test_property3_unsupported_mime_types_produce_error(mime_type):
    """Unsupported MIME types produce file_type='error'."""
    f = MockFile("bad_file.xyz", mime_type, b"some data")
    result = handle_uploaded_files([f])
    assert len(result) == 1
    assert result[0].file_type == "error"


# ---------------------------------------------------------------------------
# Property 4: Field Completeness
# **Validates: Requirements 2.3**
# ---------------------------------------------------------------------------

@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=50)
def test_property4_non_error_inputs_have_required_fields(n):
    """Every non-error InvoiceInput has non-null filename, file_type, content."""
    files = [make_mock_image(f"invoice_{i}.jpg") for i in range(n)]
    results = handle_uploaded_files(files)
    for inp in results:
        if inp.file_type != "error":
            assert inp.filename is not None
            assert inp.file_type is not None
            assert inp.content is not None


# ---------------------------------------------------------------------------
# Property 5: Error Record on Failure
# **Validates: Requirements 1.7**
# ---------------------------------------------------------------------------

@given(st.sampled_from(UNSUPPORTED_MIME_TYPES))
@settings(max_examples=50)
def test_property5_unsupported_type_produces_error_record_not_dropped(mime_type):
    """Unsupported MIME type produces InvoiceInput(file_type='error'), not a dropped file."""
    f = MockFile("unsupported.xyz", mime_type, b"data")
    result = handle_uploaded_files([f])
    # File must NOT be dropped — exactly 1 result
    assert len(result) == 1
    assert result[0].file_type == "error"
