# Requirements Document

## Introduction

BillBrain AI is a comprehensive upgrade of the existing Invoice Extractor project. It transforms a single-file Q&A tool into a full-featured, multi-phase AI finance assistant. The system supports batch invoice processing (images and PDFs), structured data extraction via Gemini 2.5 Flash, smart dashboards, duplicate detection, multi-language support, user authentication, persistent storage, and email alerting. The upgrade is backward-compatible with the existing codebase and is rolled out across three phases.

## Glossary

- **System**: The BillBrain AI application
- **File_Handler**: The component responsible for accepting, validating, and normalizing uploaded invoice files
- **Gemini_Client**: The component that wraps the Gemini 2.5 Flash API for structured invoice extraction
- **Structured_Extractor**: The component that parses Gemini output into typed InvoiceRecord objects and computes confidence scores
- **Duplicate_Checker**: The component that detects duplicate invoices within a session or across stored history
- **Dashboard_Engine**: The component that aggregates extracted invoice records into summary statistics
- **Export_Engine**: The component that converts InvoiceRecord lists to CSV or Excel format
- **Storage_Layer**: The component that persists invoice records per authenticated user (Phase 3)
- **Email_Alert_System**: The component that sends due-date reminder emails (Phase 3)
- **Auth_Layer**: The Google OAuth authentication layer (Phase 3)
- **InvoiceRecord**: A structured data object representing a single extracted invoice
- **InvoiceInput**: A normalized representation of an uploaded file ready for Gemini processing
- **ConfidenceReport**: A per-field and overall confidence assessment for an extracted InvoiceRecord
- **DuplicateResult**: The result of a duplicate check, including a flag and reference to the matching record
- **DashboardSummary**: Aggregated statistics computed from a list of InvoiceRecord objects
- **Session**: A single user's active Streamlit session, holding extracted records in st.session_state

---

## Requirements

### Requirement 1: Multi-File Upload and Validation

**User Story:** As a user, I want to upload up to 20 invoice files at once, so that I can process a batch of invoices in a single session.

#### Acceptance Criteria

1. THE File_Handler SHALL accept between 1 and 20 files per upload batch.
2. WHEN a user uploads more than 20 files, THE File_Handler SHALL raise a FileLimitExceededError and reject the entire batch before any processing begins.
3. THE File_Handler SHALL accept files of MIME types `image/jpeg`, `image/png`, and `application/pdf` only.
4. WHEN a file with an unsupported MIME type is uploaded, THE System SHALL skip that file and display a per-file warning: "⚠️ [filename] is not a supported format (jpg, png, pdf)."
5. THE File_Handler SHALL validate that each file does not exceed 10MB in size.
6. WHEN File_Handler processes a batch, THE File_Handler SHALL return a list of InvoiceInput objects where `len(result) == len(valid_files)`.
7. IF a file cannot be normalized, THEN THE File_Handler SHALL produce an InvoiceInput with `file_type = "error"` rather than silently dropping the file.

---

### Requirement 2: File Normalization

**User Story:** As a developer, I want uploaded files normalized into a consistent InvoiceInput format, so that the Gemini Client can process any file type uniformly.

#### Acceptance Criteria

1. WHEN an image file is uploaded, THE File_Handler SHALL convert it to a Gemini-compatible inline_data dict.
2. WHEN a PDF file is uploaded, THE File_Handler SHALL extract its text content using PyPDF2 and store it as a string in `InvoiceInput.content`.
3. THE File_Handler SHALL populate `InvoiceInput.filename`, `InvoiceInput.file_type`, and `InvoiceInput.content` for every processed file.

---

### Requirement 3: Structured Invoice Extraction

**User Story:** As a user, I want the system to automatically extract structured data from my invoices, so that I can see organized invoice information without manual data entry.

#### Acceptance Criteria

1. WHEN an InvoiceInput is provided, THE Gemini_Client SHALL send a structured extraction prompt to Gemini 2.5 Flash and return a raw JSON string.
2. THE Gemini_Client SHALL extract the following fields: `vendor`, `invoice_date` (YYYY-MM-DD), `items` (list), `total_amount` (float), `tax_amount` (float), `due_date` (YYYY-MM-DD), `currency` (default "INR"), and `detected_language` (ISO 639-1 code).
3. WHEN the Gemini API call fails, THE Gemini_Client SHALL retry up to 3 times with exponential backoff (2s, 4s, 8s).
4. IF all 3 retry attempts fail, THEN THE Gemini_Client SHALL return a null result and THE System SHALL create a failed InvoiceRecord with all fields set to None and `confidence.overall = "Low"`.
5. THE Gemini_Client SHALL manage API key configuration exclusively via `st.secrets`.

---

### Requirement 4: Extraction Result Parsing

**User Story:** As a developer, I want Gemini's raw output parsed into a typed InvoiceRecord, so that downstream components can work with structured data.

#### Acceptance Criteria

1. WHEN a valid JSON string is provided, THE Structured_Extractor SHALL parse it into a fully populated InvoiceRecord.
2. WHEN a malformed or non-JSON string is provided, THE Structured_Extractor SHALL attempt regex-based field extraction as a fallback.
3. IF both JSON parsing and regex fallback fail, THEN THE Structured_Extractor SHALL return an InvoiceRecord with all fields set to None and `confidence.overall = "Low"`.
4. THE Structured_Extractor SHALL never raise an exception from `parse_extraction_result`; it SHALL always return a valid InvoiceRecord.
5. THE Structured_Extractor SHALL assign a fresh UUID to `invoice_id` for every parsed InvoiceRecord.

---

### Requirement 5: Confidence Scoring

**User Story:** As a user, I want to see a confidence score for each extracted field, so that I can quickly identify which data may need manual verification.

#### Acceptance Criteria

1. THE Structured_Extractor SHALL compute a ConfidenceReport for every InvoiceRecord.
2. WHEN a field is present and passes format validation, THE Structured_Extractor SHALL assign `"High"` confidence to that field.
3. WHEN a field is present but fails format validation (e.g., ambiguous date), THE Structured_Extractor SHALL assign `"Medium"` confidence to that field.
4. WHEN a field is null or empty, THE Structured_Extractor SHALL assign `"Low"` confidence to that field.
5. THE Structured_Extractor SHALL set `ConfidenceReport.overall` to the lowest confidence level across all individual field scores.
6. WHEN all fields have `"High"` confidence, THE Structured_Extractor SHALL set `overall = "High"`.

---

### Requirement 6: Duplicate Detection

**User Story:** As a user, I want the system to detect duplicate invoices, so that I am warned before accidentally processing the same invoice twice.

#### Acceptance Criteria

1. WHEN an InvoiceRecord is processed, THE Duplicate_Checker SHALL compare it against all existing records in the current session and stored history.
2. THE Duplicate_Checker SHALL consider two records duplicates if and only if their normalized vendor names match, their total amounts are within ±0.01 float tolerance, and their invoice dates are equal.
3. THE Duplicate_Checker SHALL normalize vendor names by converting to lowercase and stripping leading/trailing whitespace before comparison.
4. WHEN a duplicate is detected, THE Duplicate_Checker SHALL return a DuplicateResult with `is_duplicate = True` and the `matching_invoice_id` and `matching_filename` of the original record.
5. WHEN no duplicate is found, THE Duplicate_Checker SHALL return a DuplicateResult with `is_duplicate = False`.
6. WHEN a duplicate invoice is detected, THE System SHALL highlight the corresponding row in yellow in the results table with a tooltip: "⚠️ Possible duplicate of [original filename]."

---

### Requirement 7: Batch Processing Pipeline

**User Story:** As a user, I want all uploaded invoices processed in a single batch operation, so that I can extract data from multiple invoices without repeated manual steps.

#### Acceptance Criteria

1. WHEN a batch of files is submitted, THE System SHALL process each file sequentially through File_Handler, Gemini_Client, Structured_Extractor, and Duplicate_Checker.
2. THE System SHALL produce exactly one InvoiceRecord per uploaded file, including files that fail extraction.
3. WHEN processing a batch, THE System SHALL display a progress indicator to the user.
4. THE System SHALL store all extracted InvoiceRecord objects in `st.session_state` to prevent re-processing on tab switches.

---

### Requirement 8: Results Display

**User Story:** As a user, I want to see extracted invoice data in a structured table, so that I can review all invoice information at a glance.

#### Acceptance Criteria

1. WHEN extraction is complete, THE System SHALL display results in a table with columns: Vendor, Date, Items, Amount, Tax, Due Date, and Confidence.
2. THE System SHALL display confidence badges per field in the results table.
3. WHEN a row represents a duplicate invoice, THE System SHALL highlight that row in yellow.
4. WHEN extraction fails for a file, THE System SHALL display "Extraction failed" in the affected field cells.

---

### Requirement 9: Export Functionality

**User Story:** As a user, I want to download extracted invoice data as CSV or Excel, so that I can use the data in other tools like spreadsheets or accounting software.

#### Acceptance Criteria

1. THE Export_Engine SHALL provide a CSV export that returns UTF-8 encoded bytes compatible with `st.download_button`.
2. THE Export_Engine SHALL provide an Excel export that returns bytes in `.xlsx` format using openpyxl.
3. THE Export_Engine SHALL map all InvoiceRecord fields to column headers in the exported file.
4. WHEN an InvoiceRecord field is None, THE Export_Engine SHALL output an empty string in the corresponding cell.
5. WHEN the records list is empty, THE Export_Engine SHALL return a valid empty CSV or Excel file without raising an exception.

---

### Requirement 10: Multi-Language Invoice Support

**User Story:** As a user, I want the system to extract data from invoices in multiple languages, so that I can process invoices regardless of the language they are written in.

#### Acceptance Criteria

1. THE Gemini_Client SHALL construct extraction prompts that instruct Gemini to detect the invoice language before extracting fields.
2. THE System SHALL support invoice extraction for invoices written in English, Hindi, Tamil, and Marathi at minimum.
3. THE Structured_Extractor SHALL populate `InvoiceRecord.detected_language` with the ISO 639-1 language code returned by Gemini.

---

### Requirement 11: Dashboard

**User Story:** As a user, I want a summary dashboard of my invoice data, so that I can quickly understand my spending patterns and identify overdue invoices.

#### Acceptance Criteria

1. THE Dashboard_Engine SHALL compute `total_spent_this_month` as the sum of `total_amount` for all InvoiceRecords where `invoice_date` falls in the current calendar month.
2. WHEN no records exist for the current month, THE Dashboard_Engine SHALL set `total_spent_this_month = 0.0`.
3. THE Dashboard_Engine SHALL identify `top_vendor` as the vendor with the highest total spend across all records.
4. WHEN the records list is empty, THE Dashboard_Engine SHALL set `top_vendor = None`.
5. THE Dashboard_Engine SHALL populate `overdue_invoices` with all InvoiceRecords where `due_date < datetime.date.today()`.
6. THE Dashboard_Engine SHALL compute `invoice_count_by_month` as a dict mapping "YYYY-MM" strings to invoice counts.
7. THE System SHALL display the dashboard summary using Streamlit metric components showing Total Spent, Top Vendor, and Overdue count.

---

### Requirement 12: Tabbed UI Layout

**User Story:** As a user, I want a clear tabbed interface, so that I can navigate between uploading, reviewing results, viewing history, and the dashboard without confusion.

#### Acceptance Criteria

1. THE System SHALL present a tabbed interface with four tabs: Upload, Results, History, and Dashboard.
2. THE System SHALL display the Upload tab with a multi-file drag-and-drop area accepting up to 20 files.
3. THE System SHALL display the Results tab with the extracted data table and download buttons.
4. THE System SHALL display the Dashboard tab with summary metrics.
5. WHEN a user is not authenticated, THE System SHALL display the History tab as requiring login.

---

### Requirement 13: Persistent Storage (Phase 3)

**User Story:** As an authenticated user, I want my invoice history persisted across sessions, so that I can access previously processed invoices without re-uploading them.

#### Acceptance Criteria

1. WHEN an authenticated user processes an invoice, THE Storage_Layer SHALL save the InvoiceRecord to the database and return a generated `invoice_id`.
2. WHEN an authenticated user opens the application, THE Storage_Layer SHALL retrieve all InvoiceRecords associated with that user's `user_id`.
3. THE Storage_Layer SHALL enforce user-scoped data isolation so that no user can access another user's InvoiceRecords.
4. WHEN a user deletes an invoice, THE Storage_Layer SHALL soft-delete the record rather than permanently removing it.
5. THE Storage_Layer SHALL support both SQLite (local) and Supabase (cloud) as backend options.
6. THE Storage_Layer SHALL use parameterized queries for all database operations to prevent SQL injection.

---

### Requirement 14: Google OAuth Authentication (Phase 3)

**User Story:** As a user, I want to log in with my Google account, so that my invoice data is securely associated with my identity.

#### Acceptance Criteria

1. THE Auth_Layer SHALL authenticate users via Google OAuth and return a `user_id` and email token upon success.
2. WHEN authentication succeeds, THE System SHALL store the OAuth token in `st.session_state` only and never persist it to the database.
3. WHEN a user logs out, THE System SHALL clear all session state.
4. WHEN an OAuth token is invalid or expired, THE Auth_Layer SHALL clear session state and redirect the user to the login page.
5. WHEN an authentication failure occurs, THE System SHALL display: "🔒 Session expired. Please log in again."

---

### Requirement 15: Email Due-Date Alerts (Phase 3)

**User Story:** As a user, I want to receive email reminders before invoice due dates, so that I never miss a payment deadline.

#### Acceptance Criteria

1. THE Email_Alert_System SHALL query the Storage_Layer for all invoices where `due_date - today <= 3 days` for a given user.
2. WHEN a due-date reminder is triggered, THE Email_Alert_System SHALL send an email containing the vendor name, total amount, and due date.
3. THE Email_Alert_System SHALL track sent alerts to prevent sending duplicate reminder emails for the same invoice.
4. WHEN an email send attempt fails, THE Email_Alert_System SHALL retry once after 60 seconds.
5. IF the retry also fails, THEN THE Email_Alert_System SHALL record `alert_status = "failed"` in the database for manual review.
6. THE Email_Alert_System SHALL store SMTP and SendGrid credentials exclusively in `st.secrets`.
