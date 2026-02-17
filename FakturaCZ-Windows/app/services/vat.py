"""VAT calculation engine with Czech rounding rules."""

from decimal import Decimal, ROUND_HALF_EVEN

from app.models.enums import VATRate
from app.models.invoice import InvoiceLine


def czech_round(value: Decimal) -> Decimal:
    """Czech rounding: mathematical rounding to 2 decimal places."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def vat_amount(base: Decimal, rate: VATRate) -> Decimal:
    return czech_round(base * rate.multiplier)


def total_with_vat(base: Decimal, rate: VATRate) -> Decimal:
    return base + vat_amount(base, rate)


def breakdown(lines: list[InvoiceLine]) -> dict[VATRate, tuple[Decimal, Decimal]]:
    """Aggregate lines into VAT breakdown: rate -> (base, vat)."""
    result: dict[VATRate, tuple[Decimal, Decimal]] = {}
    for line in lines:
        rate = line.vat_rate_enum
        base, vat_val = result.get(rate, (Decimal("0"), Decimal("0")))
        result[rate] = (base + line.line_total, vat_val + line.vat_amount)
    return result


def grand_total(lines: list[InvoiceLine]) -> Decimal:
    subtotal = sum((l.line_total for l in lines), Decimal("0"))
    total_vat = sum((l.vat_amount for l in lines), Decimal("0"))
    return czech_round(subtotal + total_vat)
