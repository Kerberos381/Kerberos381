"""Invoice and InvoiceLine data models."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional

from app.models.enums import VATRate, InvoiceState, InvoiceType, SupplyCode, VALID_TRANSITIONS


def _decimal_to_str(val) -> str:
    """Convert Decimal to string for JSON serialization."""
    if isinstance(val, Decimal):
        return str(val)
    return val


@dataclass
class InvoiceLine:
    """A single line item on an invoice."""

    item_description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    vat_rate: str = "STANDARD"  # VATRate enum name
    unit: str = "ks"
    sort_order: int = 0

    @property
    def vat_rate_enum(self) -> VATRate:
        return VATRate[self.vat_rate]

    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price

    @property
    def vat_amount(self) -> Decimal:
        return self.line_total * self.vat_rate_enum.multiplier

    @property
    def line_total_with_vat(self) -> Decimal:
        return self.line_total + self.vat_amount

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quantity"] = str(self.quantity)
        d["unit_price"] = str(self.unit_price)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> InvoiceLine:
        data = dict(data)
        data["quantity"] = Decimal(str(data.get("quantity", "1")))
        data["unit_price"] = Decimal(str(data.get("unit_price", "0")))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _czech_round(value: Decimal) -> Decimal:
    """Czech rounding: mathematical rounding to 2 decimal places."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


@dataclass
class Invoice:
    """An invoice document with child line items."""

    # Identifiers
    invoice_number: str

    # Type & State
    type: str = "STANDARD"  # InvoiceType enum name
    state: str = "OPEN"  # InvoiceState enum name

    # Dates (ISO format strings for JSON serialization)
    issued_date: str = field(default_factory=lambda: date.today().isoformat())
    taxable_supply_date: str = field(default_factory=lambda: date.today().isoformat())
    due_date: str = field(
        default_factory=lambda: (date.today() + timedelta(days=14)).isoformat()
    )

    # Payment
    variable_symbol: Optional[str] = None
    bank_account: Optional[str] = None
    iban: Optional[str] = None
    payment_method: Optional[str] = None

    # Supply classification
    supply_code: str = "DOMESTIC"  # SupplyCode enum name

    # Notes
    note: Optional[str] = None
    footer_text: Optional[str] = None

    # Locking
    is_locked: bool = False

    # Subject reference (registration_no)
    subject_registration_no: Optional[str] = None

    # Line items
    lines: list[dict] = field(default_factory=list)

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def type_enum(self) -> InvoiceType:
        return InvoiceType[self.type]

    @property
    def state_enum(self) -> InvoiceState:
        return InvoiceState[self.state]

    def get_lines(self) -> list[InvoiceLine]:
        return [InvoiceLine.from_dict(d) for d in self.lines]

    @property
    def subtotal(self) -> Decimal:
        return sum((l.line_total for l in self.get_lines()), Decimal("0"))

    @property
    def total_vat(self) -> Decimal:
        return sum((l.vat_amount for l in self.get_lines()), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return _czech_round(self.subtotal + self.total_vat)

    @property
    def vat_breakdown(self) -> dict[VATRate, tuple[Decimal, Decimal]]:
        result: dict[VATRate, tuple[Decimal, Decimal]] = {}
        for line in self.get_lines():
            rate = line.vat_rate_enum
            base, vat = result.get(rate, (Decimal("0"), Decimal("0")))
            result[rate] = (base + line.line_total, vat + line.vat_amount)
        return result

    @property
    def is_overdue(self) -> bool:
        if self.state_enum == InvoiceState.PAID:
            return False
        return date.today() > date.fromisoformat(self.due_date)

    @property
    def is_editable(self) -> bool:
        return not self.is_locked and self.state_enum == InvoiceState.OPEN

    def can_transition(self, new_state: InvoiceState) -> bool:
        current = self.state_enum
        return new_state in VALID_TRANSITIONS.get(current, [])

    def transition(self, new_state: InvoiceState) -> bool:
        if not self.can_transition(new_state):
            return False
        self.state = new_state.name
        self.updated_at = datetime.now().isoformat()
        return True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Invoice:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
