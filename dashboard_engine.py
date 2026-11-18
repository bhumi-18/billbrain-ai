import datetime
from collections import defaultdict

from models import DashboardSummary, InvoiceRecord


def compute_dashboard(records: list[InvoiceRecord]) -> DashboardSummary:
    """
    Computes:
    - total_spent_this_month: sum of total_amount where invoice_date is in current calendar month
    - top_vendor: vendor with highest total spend across all records
    - top_vendor_amount: the total spend for the top vendor
    - overdue_invoices: records where due_date < datetime.date.today()
    - invoice_count_by_month: dict mapping "YYYY-MM" -> count
    """
    today = datetime.date.today()

    # total_spent_this_month
    total_spent_this_month = 0.0
    for r in records:
        if (
            isinstance(r.invoice_date, datetime.date)
            and r.invoice_date.year == today.year
            and r.invoice_date.month == today.month
            and r.total_amount is not None
        ):
            total_spent_this_month += float(r.total_amount)

    # top_vendor: vendor with highest cumulative total_amount
    vendor_totals: dict[str, float] = defaultdict(float)
    for r in records:
        if r.vendor and r.total_amount is not None:
            vendor_totals[r.vendor] += float(r.total_amount)

    if vendor_totals:
        top_vendor = max(vendor_totals, key=lambda v: vendor_totals[v])
        top_vendor_amount = vendor_totals[top_vendor]
    else:
        top_vendor = None
        top_vendor_amount = 0.0

    # overdue_invoices
    overdue_invoices = [
        r for r in records
        if isinstance(r.due_date, datetime.date) and r.due_date < today
    ]

    # invoice_count_by_month
    invoice_count_by_month: dict[str, int] = defaultdict(int)
    for r in records:
        if isinstance(r.invoice_date, datetime.date):
            key = r.invoice_date.strftime("%Y-%m")
            invoice_count_by_month[key] += 1

    return DashboardSummary(
        total_spent_this_month=total_spent_this_month,
        top_vendor=top_vendor,
        top_vendor_amount=top_vendor_amount,
        overdue_invoices=overdue_invoices,
        invoice_count_by_month=dict(invoice_count_by_month),
    )
