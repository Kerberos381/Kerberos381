"""Daily overdue checker — transitions invoices past due date."""

from datetime import date

from app.models.enums import InvoiceState
from app.services import persistence


def check_overdue() -> int:
    """Check all non-paid invoices and mark overdue ones. Returns count."""
    invoices = persistence.load_invoices()
    today = date.today()
    count = 0

    for inv in invoices:
        if inv.state_enum in (InvoiceState.OPEN, InvoiceState.SENT):
            if today > date.fromisoformat(inv.due_date):
                inv.transition(InvoiceState.OVERDUE)
                count += 1

    if count > 0:
        persistence.save_invoices(invoices)

    return count
