"""
File Handler for BillBrain AI.
Validates, normalizes, and converts uploaded files into InvoiceInput objects.
"""

import base64
import PyPDF2

from models import InvoiceInput

# Accepted MIME types
ACCEPTED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}

# Max file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # bytes

# Max number of files per batch
MAX_FILE_COUNT = 20


class FileLimitExceededError(Exception):
    """Raised when more than 20 files are submitted in a single batch."""


def input_image_setup(file) -> dict:
    """Returns a Gemini-compatible image part dict with base64-encoded data."""
    byte_data = file.getvalue()
    return {
        "mime_type": file.type,
        "data": base64.b64encode(byte_data).decode("utf-8"),
    }


def extract_pdf_text(file) -> str:
    """Extracts raw text from all pages of a PDF using PyPDF2."""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text


def handle_uploaded_files(files: list) -> list[InvoiceInput]:
    """
    Accepts a list of Streamlit UploadedFile objects.
    Returns a list of InvoiceInput objects ready for extraction.

    Raises:
        FileLimitExceededError: if len(files) > 20
    """
    if len(files) > MAX_FILE_COUNT:
        raise FileLimitExceededError(
            f"Maximum {MAX_FILE_COUNT} files allowed per batch. "
            f"Please reduce your selection."
        )

    results: list[InvoiceInput] = []

    for file in files:
        filename = getattr(file, "name", "unknown")

        # --- MIME type validation ---
        mime_type = getattr(file, "type", "")
        if mime_type not in ACCEPTED_MIME_TYPES:
            results.append(
                InvoiceInput(
                    filename=filename,
                    file_type="error",
                    content="Unsupported file type",
                    detected_language="",
                )
            )
            continue

        # --- File size validation ---
        try:
            byte_data = file.getvalue()
        except Exception as exc:
            results.append(
                InvoiceInput(
                    filename=filename,
                    file_type="error",
                    content=f"Could not read file: {exc}",
                    detected_language="",
                )
            )
            continue

        if len(byte_data) > MAX_FILE_SIZE:
            results.append(
                InvoiceInput(
                    filename=filename,
                    file_type="error",
                    content="File too large (max 10MB)",
                    detected_language="",
                )
            )
            continue

        # --- Normalize to InvoiceInput ---
        try:
            if mime_type == "application/pdf":
                content = extract_pdf_text(file)
                file_type = "pdf"
            else:
                content = input_image_setup(file)
                file_type = "image"

            results.append(
                InvoiceInput(
                    filename=filename,
                    file_type=file_type,
                    content=content,
                    detected_language="",
                )
            )
        except Exception as exc:
            results.append(
                InvoiceInput(
                    filename=filename,
                    file_type="error",
                    content=f"Normalization failed: {exc}",
                    detected_language="",
                )
            )

    return results
