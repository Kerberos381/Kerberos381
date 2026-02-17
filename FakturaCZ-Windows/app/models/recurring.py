"""Recurring invoice template model."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from app.models.enums import RecurrencePeriod, SupplyCode


CZECH_MONTHS = [
    "leden", "únor", "březen", "duben", "květen", "červen",
    "červenec", "srpen", "září", "říjen", "listopad", "prosinec",
]


@dataclass
class LineItemSpec:
    """Serializable line item template."""
    description: str
    quantity: str = "1"
    unit_price: str = "0"
    vat_rate: str = "STANDARD"
    unit: str = "ks"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> LineItemSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RecurringTemplate:
    """A recurring invoice template that generates new invoices on a schedule."""

    template_name: str
    period: str = "MONTHLY"  # RecurrencePeriod enum name
    start_date: str = field(default_factory=lambda: date.today().isoformat())
    next_occurrence_date: str = field(default_factory=lambda: date.today().isoformat())
    end_date: Optional[str] = None
    is_active: bool = True

    # Invoice template attributes
    line_description_template: str = ""
    default_note: Optional[str] = None
    payment_term_days: int = 14
    supply_code: str = "DOMESTIC"

    # Line items template
    line_items: list[dict] = field(default_factory=list)

    # Subject reference
    subject_registration_no: Optional[str] = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_generated_at: Optional[str] = None

    @property
    def period_enum(self) -> RecurrencePeriod:
        return RecurrencePeriod[self.period]

    def resolve_description(self, for_date: date) -> str:
        month = for_date.month
        year = for_date.year
        text = self.line_description_template
        text = text.replace("{month}", CZECH_MONTHS[month - 1])
        text = text.replace("{month_num}", str(month))
        text = text.replace("{year}", str(year))
        return text

    @property
    def is_due_today(self) -> bool:
        if not self.is_active:
            return False
        return date.fromisoformat(self.next_occurrence_date) == date.today()

    def advance(self) -> None:
        from dateutil.relativedelta import relativedelta

        current = date.fromisoformat(self.next_occurrence_date)
        period = self.period_enum

        if period == RecurrencePeriod.WEEKLY:
            next_date = current + relativedelta(weeks=1)
        elif period == RecurrencePeriod.MONTHLY:
            next_date = current + relativedelta(months=1)
        elif period == RecurrencePeriod.QUARTERLY:
            next_date = current + relativedelta(months=3)
        else:
            next_date = current + relativedelta(years=1)

        self.next_occurrence_date = next_date.isoformat()
        self.last_generated_at = datetime.now().isoformat()

        if self.end_date and next_date > date.fromisoformat(self.end_date):
            self.is_active = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> RecurringTemplate:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
