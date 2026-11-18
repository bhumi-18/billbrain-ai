"""
Storage Layer for BillBrain AI.

Provides an abstract StorageBackend with two implementations:
- SQLiteBackend: local SQLite database (default)
- SupabaseBackend: stub that raises NotImplementedError

Backend is selected via st.secrets["STORAGE_BACKEND"] ("sqlite" or "supabase").
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional

from models import ConfidenceReport, InvoiceRecord

# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """Abstract interface for invoice persistence."""

    @abstractmethod
    def save_invoice(self, user_id: str, record: InvoiceRecord) -> str:
        """Persist *record* for *user_id*; return the invoice_id."""

    @abstractmethod
    def get_user_invoices(self, user_id: str) -> list[InvoiceRecord]:
        """Return all non-deleted invoices belonging to *user_id*."""

    @abstractmethod
    def delete_invoice(self, invoice_id: str) -> bool:
        """Soft-delete the invoice; return True on success."""


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT,
    vendor TEXT,
    invoice_date TEXT,
    items TEXT,
    total_amount REAL,
    tax_amount REAL,
    due_date TEXT,
    currency TEXT DEFAULT 'INR',
    detected_language TEXT,
    confidence_overall TEXT,
    extracted_at TEXT,
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of TEXT,
    deleted INTEGER DEFAULT 0
)
"""


class SQLiteBackend(StorageBackend):
    """SQLite-backed storage using a local ``billbrain.db`` file."""

    def __init__(self, db_path: str = "billbrain.db") -> None:
        self._db_path = db_path
        # For in-memory databases we must reuse a single connection because
        # each new sqlite3.connect(":memory:") creates an independent DB.
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        conn.execute(_CREATE_TABLE_SQL)
        conn.commit()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def save_invoice(self, user_id: str, record: InvoiceRecord) -> str:
        """Insert or replace the invoice record; return its invoice_id."""
        invoice_id = record.invoice_id or str(uuid.uuid4())

        items_json = json.dumps(record.items) if record.items is not None else "[]"
        invoice_date_str = str(record.invoice_date) if record.invoice_date else ""
        due_date_str = str(record.due_date) if record.due_date else ""
        confidence_overall = record.confidence.overall if record.confidence else "Low"
        extracted_at_str = (
            record.extracted_at.isoformat() if record.extracted_at else datetime.utcnow().isoformat()
        )

        sql = """
            INSERT OR REPLACE INTO invoices (
                invoice_id, user_id, filename, vendor, invoice_date,
                items, total_amount, tax_amount, due_date, currency,
                detected_language, confidence_overall, extracted_at,
                is_duplicate, duplicate_of, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """
        params = (
            invoice_id,
            user_id,
            record.filename,
            record.vendor,
            invoice_date_str,
            items_json,
            record.total_amount,
            record.tax_amount,
            due_date_str,
            record.currency,
            record.detected_language,
            confidence_overall,
            extracted_at_str,
            int(record.is_duplicate),
            record.duplicate_of,
        )

        conn = self._connect()
        conn.execute(sql, params)
        conn.commit()

        return invoice_id

    def get_user_invoices(self, user_id: str) -> list[InvoiceRecord]:
        """Return all non-deleted invoices for *user_id*."""
        sql = """
            SELECT * FROM invoices
            WHERE user_id = ? AND deleted = 0
            ORDER BY extracted_at DESC
        """
        conn = self._connect()
        rows = conn.execute(sql, (user_id,)).fetchall()

        return [self._row_to_record(dict(row)) for row in rows]

    def delete_invoice(self, invoice_id: str) -> bool:
        """Soft-delete: set deleted = 1 for the given invoice_id."""
        sql = "UPDATE invoices SET deleted = 1 WHERE invoice_id = ?"
        conn = self._connect()
        cursor = conn.execute(sql, (invoice_id,))
        conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Deserialization
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _row_to_record(row: dict) -> InvoiceRecord:
        overall = row.get("confidence_overall") or "Low"
        confidence = ConfidenceReport(
            vendor=overall,
            invoice_date=overall,
            total_amount=overall,
            tax_amount=overall,
            due_date=overall,
            items=overall,
            overall=overall,
        )

        items_raw = row.get("items") or "[]"
        try:
            items = json.loads(items_raw)
        except (json.JSONDecodeError, TypeError):
            items = []

        extracted_at_raw = row.get("extracted_at") or ""
        try:
            extracted_at = datetime.fromisoformat(extracted_at_raw)
        except (ValueError, TypeError):
            extracted_at = datetime.utcnow()

        return InvoiceRecord(
            invoice_id=row["invoice_id"],
            user_id=row.get("user_id"),
            filename=row.get("filename") or "",
            vendor=row.get("vendor"),
            invoice_date=SQLiteBackend._parse_date(row.get("invoice_date")),
            items=items,
            total_amount=row.get("total_amount"),
            tax_amount=row.get("tax_amount"),
            due_date=SQLiteBackend._parse_date(row.get("due_date")),
            currency=row.get("currency") or "INR",
            detected_language=row.get("detected_language") or "en",
            confidence=confidence,
            extracted_at=extracted_at,
            is_duplicate=bool(row.get("is_duplicate", 0)),
            duplicate_of=row.get("duplicate_of"),
        )


# ---------------------------------------------------------------------------
# Supabase backend (stub)
# ---------------------------------------------------------------------------

class SupabaseBackend(StorageBackend):
    """Supabase-backed storage stub.

    Full implementation requires ``supabase-py`` and valid credentials
    configured in ``st.secrets``.
    """

    def save_invoice(self, user_id: str, record: InvoiceRecord) -> str:
        raise NotImplementedError(
            "Configure SUPABASE_URL and SUPABASE_KEY in st.secrets to use Supabase backend."
        )

    def get_user_invoices(self, user_id: str) -> list[InvoiceRecord]:
        raise NotImplementedError(
            "Configure SUPABASE_URL and SUPABASE_KEY in st.secrets to use Supabase backend."
        )

    def delete_invoice(self, invoice_id: str) -> bool:
        raise NotImplementedError(
            "Configure SUPABASE_URL and SUPABASE_KEY in st.secrets to use Supabase backend."
        )


# ---------------------------------------------------------------------------
# Backend factory & module-level singleton
# ---------------------------------------------------------------------------

def get_storage_backend() -> StorageBackend:
    """Return the configured storage backend.

    Reads ``STORAGE_BACKEND`` from ``st.secrets`` (defaults to ``"sqlite"``).
    Falls back to SQLiteBackend if Streamlit is not available (e.g. in tests).
    """
    try:
        import streamlit as st
        backend_type: str = st.secrets.get("STORAGE_BACKEND", "sqlite")
    except Exception:
        backend_type = "sqlite"

    if backend_type == "supabase":
        return SupabaseBackend()
    return SQLiteBackend()


# Module-level singleton — import and use directly:
#   from storage import storage
#   storage.save_invoice(user_id, record)
storage = get_storage_backend()
