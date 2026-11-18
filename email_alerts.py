"""
Email Alert System for BillBrain AI.

Sends due-date reminder emails 3 days before invoice due dates.
Tracks sent alerts in the DB to prevent duplicates.
Supports smtplib (local) and SendGrid (production) backends.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB helpers — email_alerts table
# ---------------------------------------------------------------------------

_CREATE_ALERTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS email_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    sent_at TEXT,
    alert_status TEXT DEFAULT 'pending',
    UNIQUE(invoice_id, user_id)
)
"""


def _get_db_path() -> str:
    """Return the configured DB path (same as storage layer)."""
    try:
        import streamlit as st
        return st.secrets.get("DB_PATH", "billbrain.db")
    except Exception:
        return "billbrain.db"


def _init_alerts_table(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_ALERTS_TABLE_SQL)
    conn.commit()


def _is_already_sent(conn: sqlite3.Connection, invoice_id: str, user_id: str) -> bool:
    row = conn.execute(
        "SELECT alert_status FROM email_alerts WHERE invoice_id = ? AND user_id = ?",
        (invoice_id, user_id),
    ).fetchone()
    return row is not None and row[0] == "sent"


def _upsert_alert_status(
    conn: sqlite3.Connection,
    invoice_id: str,
    user_id: str,
    status: str,
    sent_at: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO email_alerts (invoice_id, user_id, sent_at, alert_status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(invoice_id, user_id) DO UPDATE SET
            alert_status = excluded.alert_status,
            sent_at = excluded.sent_at
        """,
        (invoice_id, user_id, sent_at, status),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Email composition
# ---------------------------------------------------------------------------

def _compose_email(vendor: str, total_amount: Optional[float], currency: str, due_date: date) -> tuple[str, str]:
    """Return (subject, body) for a reminder email."""
    amount_str = f"{currency} {total_amount:.2f}" if total_amount is not None else f"{currency} N/A"
    subject = f"🔔 Invoice Due Soon: {vendor} — {due_date}"
    body = (
        f"Hi,\n\n"
        f"This is a reminder that the following invoice is due soon:\n\n"
        f"Vendor: {vendor}\n"
        f"Amount: {amount_str}\n"
        f"Due Date: {due_date}\n\n"
        f"Please ensure payment is made on time.\n\n"
        f"— BillBrain AI"
    )
    return subject, body


# ---------------------------------------------------------------------------
# Backend senders
# ---------------------------------------------------------------------------

def _send_via_smtp(to_email: str, subject: str, body: str) -> None:
    """Send email using smtplib. Reads credentials from st.secrets."""
    import smtplib
    from email.mime.text import MIMEText

    import streamlit as st

    smtp_host = st.secrets.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(st.secrets.get("SMTP_PORT", 587))
    smtp_user = st.secrets["SMTP_USER"]
    smtp_pass = st.secrets["SMTP_PASS"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())


def _send_via_sendgrid(to_email: str, subject: str, body: str) -> None:
    """Send email using SendGrid. Reads API key from st.secrets."""
    try:
        import streamlit as st
        api_key = st.secrets.get("SENDGRID_API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        raise NotImplementedError(
            "SendGrid is not configured. Set SENDGRID_API_KEY in st.secrets."
        )

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError as exc:
        raise NotImplementedError(
            "sendgrid package is not installed. Run: pip install sendgrid"
        ) from exc

    message = Mail(
        from_email="noreply@billbrain.ai",
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    sg = SendGridAPIClient(api_key)
    sg.send(message)


def _send_email(to_email: str, subject: str, body: str, backend: str) -> None:
    """Dispatch to the correct email backend."""
    if backend == "sendgrid":
        _send_via_sendgrid(to_email, subject, body)
    else:
        _send_via_smtp(to_email, subject, body)


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

def _send_with_retry(
    to_email: str,
    subject: str,
    body: str,
    backend: str,
    retry_delay: int = 60,
) -> bool:
    """
    Attempt to send email. On failure, wait retry_delay seconds and try once more.
    Returns True on success, False if both attempts fail.
    """
    for attempt in range(2):
        try:
            _send_email(to_email, subject, body, backend)
            return True
        except Exception as exc:
            logger.warning("Email send attempt %d failed: %s", attempt + 1, exc)
            if attempt == 0:
                logger.info("Retrying in %d seconds…", retry_delay)
                time.sleep(retry_delay)

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_and_send_reminders(user_id: str, user_email: str) -> list[str]:
    """
    Queries invoices due within 3 days.
    Sends reminder email for each (with deduplication and retry).
    Returns list of invoice_ids that triggered alerts.
    """
    # Graceful fallback: if Streamlit secrets are unavailable, skip sending.
    try:
        import streamlit as st
        email_backend: str = st.secrets.get("EMAIL_BACKEND", "smtp")
    except Exception:
        logger.warning(
            "Streamlit secrets not available — skipping email alerts for user %s.", user_id
        )
        return []

    # Load invoices from storage
    from storage import storage
    invoices = storage.get_user_invoices(user_id)

    # Filter for invoices due within the next 3 days
    today = date.today()
    cutoff = today + timedelta(days=3)
    due_soon = [r for r in invoices if r.due_date and today <= r.due_date <= cutoff]

    if not due_soon:
        return []

    # Open a single DB connection for alert tracking
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    _init_alerts_table(conn)

    triggered: list[str] = []

    try:
        for record in due_soon:
            invoice_id = record.invoice_id

            # Deduplication: skip if already sent
            if _is_already_sent(conn, invoice_id, user_id):
                logger.debug("Alert already sent for invoice %s — skipping.", invoice_id)
                continue

            vendor = record.vendor or "Unknown Vendor"
            subject, body = _compose_email(
                vendor=vendor,
                total_amount=record.total_amount,
                currency=record.currency or "INR",
                due_date=record.due_date,
            )

            # Mark as pending before attempting send
            _upsert_alert_status(conn, invoice_id, user_id, "pending")

            success = _send_with_retry(
                to_email=user_email,
                subject=subject,
                body=body,
                backend=email_backend,
            )

            if success:
                from datetime import datetime
                sent_at = datetime.utcnow().isoformat()
                _upsert_alert_status(conn, invoice_id, user_id, "sent", sent_at)
                triggered.append(invoice_id)
                logger.info("Reminder sent for invoice %s to %s.", invoice_id, user_email)
            else:
                _upsert_alert_status(conn, invoice_id, user_id, "failed")
                logger.error(
                    "Failed to send reminder for invoice %s after retry.", invoice_id
                )
    finally:
        conn.close()

    return triggered
