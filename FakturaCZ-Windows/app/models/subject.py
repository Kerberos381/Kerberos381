"""Subject (client/supplier) data model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Subject:
    """A business subject identified by Czech registration number (IČO)."""

    # Identifiers
    registration_no: str  # IČO — 8-digit Czech business ID

    # Business details (enriched from ARES)
    name: str = ""
    street: str = ""
    city: str = ""
    zip: str = ""
    vat_no: Optional[str] = None  # DIČ

    # Contact (user-provided)
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_account: Optional[str] = None
    iban: Optional[str] = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_ares_sync: Optional[str] = None

    @property
    def is_vat_payer(self) -> bool:
        return bool(self.vat_no)

    @property
    def formatted_address(self) -> str:
        parts = [self.street, f"{self.zip} {self.city}"]
        return "\n".join(p for p in parts if p.strip())

    def apply_ares_data(self, data: dict) -> None:
        """Apply data retrieved from the ARES registry."""
        self.name = data.get("name", self.name)
        self.street = data.get("street", self.street)
        self.city = data.get("city", self.city)
        self.zip = data.get("zip", self.zip)
        self.vat_no = data.get("vat_no")
        self.last_ares_sync = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Subject:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
