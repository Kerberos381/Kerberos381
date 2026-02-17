"""Recurring invoice scheduler — generates invoices from templates."""

from datetime import date, timedelta

from app.models.invoice import Invoice, InvoiceLine
from app.models.recurring import RecurringTemplate, LineItemSpec
from app.services import persistence


def process_templates() -> list[Invoice]:
    """Check all active templates and generate invoices for those due today."""
    templates = persistence.load_recurring()
    generated: list[Invoice] = []

    for template in templates:
        if not template.is_due_today:
            continue

        invoice = _generate_invoice(template)
        generated.append(invoice)
        template.advance()

    if generated:
        persistence.save_recurring(templates)

    return generated


def _generate_invoice(template: RecurringTemplate) -> Invoice:
    today = date.today()
    number = persistence.next_invoice_number()
    due = today + timedelta(days=template.payment_term_days)

    invoice = Invoice(
        invoice_number=number,
        type="STANDARD",
        state="OPEN",
        issued_date=today.isoformat(),
        taxable_supply_date=today.isoformat(),
        due_date=due.isoformat(),
        supply_code=template.supply_code,
        subject_registration_no=template.subject_registration_no,
        note=template.default_note,
    )

    lines = []
    for i, spec_dict in enumerate(template.line_items):
        spec = LineItemSpec.from_dict(spec_dict)
        desc = template.resolve_description(today) or spec.description
        line = InvoiceLine(
            item_description=desc,
            quantity=__import__("decimal").Decimal(spec.quantity),
            unit_price=__import__("decimal").Decimal(spec.unit_price),
            vat_rate=spec.vat_rate,
            unit=spec.unit,
            sort_order=i,
        )
        lines.append(line.to_dict())

    invoice.lines = lines
    persistence.upsert_invoice(invoice)
    return invoice
