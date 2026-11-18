import streamlit as st
import pandas as pd
import google.generativeai as genai

from auth import render_login_button, get_current_user, is_authenticated
from file_handler import handle_uploaded_files, FileLimitExceededError
from gemini_client import extract_structured_invoice
from extractor import parse_extraction_result, create_failed_record
from duplicate_checker import is_duplicate
from export_engine import export_to_csv, export_to_excel
from dashboard_engine import compute_dashboard
from models import InvoiceRecord
from storage import storage

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="🧠 BillBrain AI", page_icon="🧠", layout="wide")

# ── Gemini API key ────────────────────────────────────────────────────────────
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# ── Session state init ────────────────────────────────────────────────────────
if "records" not in st.session_state:
    st.session_state.records = []

if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False

if is_authenticated() and not st.session_state.history_loaded:
    user = get_current_user()
    if user:
        historical = storage.get_user_invoices(user["user_id"])
        existing_ids = {r.invoice_id for r in st.session_state.records}
        for r in historical:
            if r.invoice_id not in existing_ids:
                st.session_state.records.append(r)
        st.session_state.history_loaded = True

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🧠 BillBrain AI")
st.caption("Your smart finance assistant that reads, understands, and organizes your bills instantly.")
render_login_button()


# ── Batch processing ──────────────────────────────────────────────────────────
def process_batch(uploaded_files: list, session_records: list[InvoiceRecord]) -> list[InvoiceRecord]:
    """
    Process a batch of uploaded files through the full extraction pipeline.
    Raises FileLimitExceededError if more than 20 files are provided.
    """
    if len(uploaded_files) > 20:
        raise FileLimitExceededError("Maximum 20 files allowed per batch. Please reduce your selection.")

    invoice_inputs = handle_uploaded_files(uploaded_files)

    results: list[InvoiceRecord] = []
    progress_bar = st.progress(0, text="Processing invoices…")
    total = len(invoice_inputs)

    for idx, invoice_input in enumerate(invoice_inputs):
        # Warn about unsupported file types but still track them
        if invoice_input.file_type == "error":
            st.warning(f"⚠️ {invoice_input.filename} is not a supported format (jpg, png, pdf).")
            record = create_failed_record(invoice_input.filename)
            results.append(record)
            progress_bar.progress((idx + 1) / total, text=f"Skipped {invoice_input.filename}")
            continue

        raw_result = extract_structured_invoice(invoice_input)

        if raw_result is None:
            st.warning(f"⚠️ Could not extract {invoice_input.filename} — API error. Please retry.")
            record = create_failed_record(invoice_input.filename)
        else:
            record = parse_extraction_result(raw_result)
            record.filename = invoice_input.filename
            dup_result = is_duplicate(record, session_records + results)
            record.is_duplicate = dup_result.is_duplicate
            record.duplicate_of = dup_result.matching_invoice_id

        results.append(record)
        # Save to persistent storage if authenticated
        if is_authenticated():
            user = get_current_user()
            if user:
                try:
                    storage.save_invoice(user["user_id"], record)
                except Exception:
                    pass  # Don't block UI on storage failure
        progress_bar.progress((idx + 1) / total, text=f"Processed {invoice_input.filename}")

    progress_bar.empty()
    return results


# ── Helpers for Results tab ───────────────────────────────────────────────────
def _records_to_df(records: list[InvoiceRecord]) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append({
            "Vendor": r.vendor or "",
            "Date": str(r.invoice_date) if r.invoice_date else "",
            "Items": ", ".join(r.items) if r.items else "",
            "Amount": r.total_amount if r.total_amount is not None else "",
            "Tax": r.tax_amount if r.tax_amount is not None else "",
            "Due Date": str(r.due_date) if r.due_date else "",
            "Confidence": r.confidence.overall if r.confidence else "",
            "Duplicate": r.is_duplicate,
        })
    return pd.DataFrame(rows)


def _highlight_duplicates(row):
    if row.get("Duplicate", False):
        return ["background-color: #fff3cd"] * len(row)
    return [""] * len(row)


# ── Login form (shown when user clicks Login button) ─────────────────────────
if st.session_state.get("show_login"):
    from auth import login
    login()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_upload, tab_results, tab_history, tab_dashboard = st.tabs(
    ["📤 Upload", "📊 Results", "🕐 History", "📈 Dashboard"]
)

# ── Upload tab ────────────────────────────────────────────────────────────────
with tab_upload:
    st.subheader("Upload Invoices")
    uploaded_files = st.file_uploader(
        "Drag & drop up to 20 invoices (jpg, png, pdf)",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        label_visibility="visible",
    )

    if st.button("🔎 Extract All Invoices", disabled=not uploaded_files):
        try:
            new_records = process_batch(uploaded_files, st.session_state.records)
            st.session_state.records = st.session_state.records + new_records
            st.success(f"✅ Extracted {len(new_records)} invoice(s). Switch to the Results tab to view them.")
        except FileLimitExceededError as exc:
            st.error(f"❌ {exc}")

# ── Results tab ───────────────────────────────────────────────────────────────
with tab_results:
    records = st.session_state.records
    if not records:
        st.info("No invoices extracted yet. Upload files in the Upload tab.")
    else:
        df = _records_to_df(records)
        display_df = df.drop(columns=["Duplicate"])
        styled = df.style.apply(_highlight_duplicates, axis=1).hide(subset=["Duplicate"], axis="columns")
        st.dataframe(styled, use_container_width=True)

        dup_count = sum(1 for r in records if r.is_duplicate)
        if dup_count:
            st.warning(f"⚠️ {dup_count} possible duplicate(s) highlighted in yellow.")

        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv_bytes = export_to_csv(records)
            st.download_button(
                label="📥 Download CSV",
                data=csv_bytes,
                file_name="invoices.csv",
                mime="text/csv",
            )
        with col_xlsx:
            xlsx_bytes = export_to_excel(records)
            st.download_button(
                label="📥 Download Excel",
                data=xlsx_bytes,
                file_name="invoices.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ── History tab ───────────────────────────────────────────────────────────────
with tab_history:
    if not is_authenticated():
        st.info("🔒 Login required to view history.")
    else:
        user = get_current_user()
        historical_records = storage.get_user_invoices(user["user_id"])

        if not historical_records:
            st.info("No invoice history yet. Upload and extract invoices to build your history.")
        else:
            st.subheader(f"📋 Invoice History ({len(historical_records)} records)")

            col_search, col_filter = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Search by vendor", placeholder="e.g. Amazon")
            with col_filter:
                confidence_filter = st.selectbox("Filter by confidence", ["All", "High", "Medium", "Low"])

            filtered = historical_records
            if search_query:
                filtered = [r for r in filtered if r.vendor and search_query.lower() in r.vendor.lower()]
            if confidence_filter != "All":
                filtered = [r for r in filtered if r.confidence and r.confidence.overall == confidence_filter]

            st.caption(f"Showing {len(filtered)} of {len(historical_records)} records")

            if filtered:
                hist_df = _records_to_df(filtered)
                st.dataframe(hist_df.drop(columns=["Duplicate"]), use_container_width=True)
            else:
                st.info("No records match your search/filter criteria.")

# ── Dashboard tab ────────────────────────────────────────────────────────────
with tab_dashboard:
    records = st.session_state.records
    if not records:
        st.info("No invoices extracted yet.")
    else:
        summary = compute_dashboard(records)
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Spent This Month", f"₹{summary.total_spent_this_month:,.2f}")
        col2.metric("🏆 Top Vendor", summary.top_vendor or "N/A")
        col3.metric("⚠️ Overdue Invoices", len(summary.overdue_invoices))
