"""Tax export record model."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TaxExportRecord:
    """Tracks accounting export batches and immutability lock triggers."""

    export_type: str  # "DPH", "KH", "ISDOC", "Pohoda"
    period_year: int
    period_month: int
    is_sharp: bool
    invoice_ids: list[str] = field(default_factory=list)
    output_file_name: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TaxExportRecord:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
