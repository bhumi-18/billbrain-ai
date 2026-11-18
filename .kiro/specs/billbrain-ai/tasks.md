# Tasks

## Phase 1: Core Upgrades

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Update `requirement.txt` with all Phase 1 dependencies: `streamlit>=1.35`, `google-generativeai>=0.8`, `PyPDF2`, `Pillow`, `pandas`, `openpyxl`, `python-dotenv`
  - [x] 1.2 Create `models.py` with `InvoiceInput`, `InvoiceRecord`, `ConfidenceReport`, `DuplicateResult`, and `DashboardSummary` dataclasses

- [x] 2. Implement File Handler (`file_handler.py`)
  - [x] 2.1 Implement `handle_uploaded_files(files)` that validates file count (1–20), rejects batches > 20 with `FileLimitExceededError`, and returns a list of `InvoiceInput` objects
  - [x] 2.2 Implement per-file MIME type validation (jpeg, png, pdf only); produce `InvoiceInput(file_type="error")` for unsupported types
  - [x] 2.3 Implement per-file size validation (max 10MB)
  - [x] 2.4 Preserve existing `input_image_setup()` and `extract_pdf_text()` functions; integrate them into `handle_uploaded_files`

- [x] 3. Implement Gemini Client (`gemini_client.py`)
  - [x] 3.1 Implement `extract_structured_invoice(invoice_input)` with the multi-language structured extraction prompt from the design
  - [x] 3.2 Implement retry logic: up to 3 attempts with exponential backoff (2s, 4s, 8s) on API errors
  - [x] 3.3 Return `None` after 3 failed attempts so the caller can create a failed record

- [x] 4. Implement Structured Extractor (`extractor.py`)
  - [x] 4.1 Implement `parse_extraction_result(raw)`: JSON parsing with regex fallback; never raises; always returns a valid `InvoiceRecord` with a fresh UUID
  - [x] 4.2 Implement `compute_confidence(record)`: assign High/Medium/Low per field based on presence and format validity; set `overall` to the minimum field confidence

- [x] 5. Implement Duplicate Checker (`duplicate_checker.py`)
  - [x] 5.1 Implement `is_duplicate(record, existing)`: normalize vendor names (lowercase + strip), compare amount within ±0.01, compare date equality; return `DuplicateResult`

- [x] 6. Implement batch processing pipeline in `app.py`
  - [x] 6.1 Replace single-file uploader with `st.file_uploader(..., accept_multiple_files=True)`
  - [x] 6.2 Implement `process_batch(uploaded_files, session_records)` following the pseudocode in the design document
  - [x] 6.3 Store results in `st.session_state` to prevent re-processing on tab switches
  - [x] 6.4 Add a progress bar (`st.progress`) during batch processing

- [x] 7. Implement Export Engine (`export_engine.py`)
  - [x] 7.1 Implement `export_to_csv(records)`: map all `InvoiceRecord` fields to columns, represent None as empty string, return UTF-8 bytes
  - [x] 7.2 Implement `export_to_excel(records)`: same field mapping, return `.xlsx` bytes using openpyxl
  - [x] 7.3 Handle empty records list gracefully (return valid empty file, no exception)

- [x] 8. Build tabbed UI layout in `app.py`
  - [x] 8.1 Implement four-tab layout: Upload, Results, History, Dashboard using `st.tabs`
  - [x] 8.2 Upload tab: drag-and-drop multi-file area with "🔎 Extract All Invoices" button
  - [x] 8.3 Results tab: `st.dataframe` table with Vendor, Date, Items, Amount, Tax, Due Date, Confidence columns; highlight duplicate rows in yellow; "📥 Download CSV" and "📥 Download Excel" buttons
  - [x] 8.4 History tab: display "Login required" placeholder for unauthenticated users

## Phase 2: Intelligence

- [x] 9. Implement Dashboard Engine (`dashboard_engine.py`)
  - [x] 9.1 Implement `compute_dashboard(records)`: compute `total_spent_this_month`, `top_vendor`, `overdue_invoices`, and `invoice_count_by_month`
  - [x] 9.2 Wire Dashboard tab in `app.py` to display `st.metric` components for Total Spent, Top Vendor, and Overdue count

- [x] 10. Add multi-language support
  - [x] 10.1 Update the Gemini extraction prompt in `gemini_client.py` to explicitly instruct language detection before field extraction
  - [x] 10.2 Add `langdetect` to `requirement.txt` as a fallback language detector
  - [x] 10.3 Populate `InvoiceRecord.detected_language` from Gemini response; fall back to `langdetect` if Gemini omits the field

## Phase 3: Production

- [x] 11. Implement Storage Layer (`storage.py`)
  - [x] 11.1 Implement `save_invoice(user_id, record)`, `get_user_invoices(user_id)`, and `delete_invoice(invoice_id)` with SQLite backend using parameterized queries
  - [x] 11.2 Add Supabase backend option behind an abstraction interface; select backend via `st.secrets`
  - [x] 11.3 Implement soft-delete (set `deleted = True` flag rather than removing rows)
  - [x] 11.4 Enforce user-scoped data isolation in all queries

- [x] 12. Implement Google OAuth Authentication (`auth.py`)
  - [x] 12.1 Integrate Google OAuth using `streamlit-google-auth` or `authlib`; store token in `st.session_state` only
  - [x] 12.2 Implement logout: clear all session state
  - [x] 12.3 Handle expired/invalid tokens: clear session and redirect to login with "🔒 Session expired. Please log in again."
  - [x] 12.4 Wire Login button in the UI header

- [x] 13. Implement Email Alert System (`email_alerts.py`)
  - [x] 13.1 Implement `check_and_send_reminders(user_id, user_email)`: query invoices due within 3 days, compose and send reminder emails
  - [x] 13.2 Track sent alerts in the DB to prevent duplicate emails
  - [x] 13.3 Implement retry-once-after-60s on send failure; record `alert_status = "failed"` if retry also fails
  - [x] 13.4 Support both smtplib (local) and SendGrid (production); select via `st.secrets`

- [x] 14. Wire History tab with persistent storage
  - [x] 14.1 For authenticated users, load historical `InvoiceRecord` objects from Storage Layer on session start
  - [x] 14.2 Display history with search and filter controls in the History tab
  - [x] 14.3 Save each newly extracted invoice to Storage Layer immediately after extraction

## Testing

- [x] 15. Write unit and property-based tests (`tests/`)
  - [x] 15.1 Write property tests for File Handler: batch size invariant (Property 1), file limit rejection (Property 2), file type acceptance (Property 3), field completeness (Property 4), error record on failure (Property 5)
  - [x] 15.2 Write property tests for Structured Extractor: never raises (Property 6), failed parse produces Low confidence (Property 7), unique invoice IDs (Property 8), confidence overall is minimum (Property 9), confidence field assignment rules (Property 10)
  - [x] 15.3 Write property tests for Duplicate Checker: duplicate detection consistency (Property 11), vendor normalization idempotence (Property 12)
  - [x] 15.4 Write property tests for Gemini Client: API retry on failure (Property 13) using mocked API
  - [x] 15.5 Write property tests for Export Engine: CSV round-trip (Property 14), export column completeness (Property 15)
  - [x] 15.6 Write property tests for Dashboard Engine: total correctness (Property 16), overdue filtering (Property 17), top vendor correctness (Property 18)
  - [x] 15.7 Write example-based unit tests for error scenarios: unsupported file type warning, malformed JSON fallback, empty export, empty dashboard
