"""Enumerations for the invoicing system."""

from enum import Enum


class VATRate(Enum):
    """Czech VAT rates."""
    ZERO = 0
    REDUCED = 12
    STANDARD = 21

    @property
    def label(self) -> str:
        return f"{self.value} %"

    @property
    def multiplier(self):
        from decimal import Decimal
        return Decimal(self.value) / Decimal(100)


class InvoiceState(Enum):
    """Invoice lifecycle states."""
    OPEN = "open"
    SENT = "sent"
    OVERDUE = "overdue"
    PAID = "paid"

    @property
    def label(self) -> str:
        labels = {
            "open": "Otevřená",
            "sent": "Odeslaná",
            "overdue": "Po splatnosti",
            "paid": "Zaplacená",
        }
        return labels[self.value]

    @property
    def color(self) -> str:
        """Color hex for UI badges."""
        colors = {
            "open": "#3B82F6",
            "sent": "#F59E0B",
            "overdue": "#EF4444",
            "paid": "#22C55E",
        }
        return colors[self.value]


class InvoiceType(Enum):
    """Invoice document types."""
    STANDARD = "standard"
    PROFORMA = "proforma"
    CREDIT = "credit"

    @property
    def label(self) -> str:
        labels = {
            "standard": "Faktura",
            "proforma": "Proforma",
            "credit": "Dobropis",
        }
        return labels[self.value]


class RecurrencePeriod(Enum):
    """Recurring invoice periods."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

    @property
    def label(self) -> str:
        labels = {
            "weekly": "Týdně",
            "monthly": "Měsíčně",
            "quarterly": "Čtvrtletně",
            "yearly": "Ročně",
        }
        return labels[self.value]


class SupplyCode(Enum):
    """Supply classification for VAT purposes."""
    DOMESTIC = "domestic"
    REVERSE_CHARGE = "reverse_charge"
    OSS = "oss"

    @property
    def label(self) -> str:
        labels = {
            "domestic": "Tuzemské plnění",
            "reverse_charge": "Přenesená daňová povinnost",
            "oss": "OSS (EU)",
        }
        return labels[self.value]


class TaxPeriod(Enum):
    """Tax reporting period."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

    @property
    def label(self) -> str:
        labels = {"monthly": "Měsíční", "quarterly": "Čtvrtletní"}
        return labels[self.value]


# Valid state transitions for the invoice state machine.
VALID_TRANSITIONS: dict[InvoiceState, list[InvoiceState]] = {
    InvoiceState.OPEN: [InvoiceState.SENT, InvoiceState.PAID],
    InvoiceState.SENT: [InvoiceState.OVERDUE, InvoiceState.PAID],
    InvoiceState.OVERDUE: [InvoiceState.PAID],
    InvoiceState.PAID: [],
}
