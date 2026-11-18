import time
import streamlit as st
import google.generativeai as genai

from models import InvoiceInput

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

EXTRACTION_PROMPT = """You are an expert invoice data extractor.
Step 1: Detect the language of this invoice (it may be in English, Hindi, Tamil, Marathi, or another language).
Step 2: Extract the following fields as a JSON object:
{
  "vendor": string or null,
  "invoice_date": "YYYY-MM-DD" or null,
  "items": [list of item descriptions as strings],
  "total_amount": float or null,
  "tax_amount": float or null,
  "due_date": "YYYY-MM-DD" or null,
  "currency": string (default "INR"),
  "detected_language": ISO 639-1 language code (e.g. "en", "hi", "ta", "mr")
}
Return ONLY the JSON object. No explanation, no markdown, no code blocks."""


def get_gemini_response(system_prompt: str, file_input: dict | str, user_prompt: str) -> str:
    """Calls Gemini 2.5 Flash and returns raw text response."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    if isinstance(file_input, dict):
        # Image: pass as inline_data part
        parts = [
            system_prompt,
            {"inline_data": file_input},
            user_prompt,
        ]
    else:
        # PDF text: pass as plain text
        parts = [system_prompt, file_input, user_prompt]
    response = model.generate_content(parts)
    return response.text


def extract_structured_invoice(invoice_input: InvoiceInput) -> str | None:
    """
    Sends a structured extraction prompt to Gemini.
    Returns raw JSON string with invoice fields.
    Returns None after 3 failed attempts.
    """
    # Delays before each retry: 2s before attempt 2, 4s before attempt 3, 8s before attempt 4 (never reached)
    retry_delays = [2, 4, 8]
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            return get_gemini_response(EXTRACTION_PROMPT, invoice_input.content, "")
        except Exception:
            if attempt < max_attempts:
                time.sleep(retry_delays[attempt - 1])

    return None
