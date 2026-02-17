"""Local JSON file persistence — all data stored in the app directory."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import TypeVar, Type

from app.models.subject import Subject
from app.models.invoice import Invoice
from app.models.recurring import RecurringTemplate
from app.models.tax_export import TaxExportRecord


def _get_data_dir() -> Path:
    """Returns the data directory next to the executable / script."""
    if getattr(__import__("sys"), "frozen", False):
        # Running as PyInstaller bundle
        base = Path(__import__("sys").executable).parent
    else:
        base = Path(__file__).resolve().parent.parent.parent

    data_dir = base / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


DATA_DIR = _get_data_dir()

SUBJECTS_FILE = DATA_DIR / "subjects.json"
INVOICES_FILE = DATA_DIR / "invoices.json"
RECURRING_FILE = DATA_DIR / "recurring.json"
EXPORTS_FILE = DATA_DIR / "exports.json"


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: list[dict]) -> None:
    # Write to temp file first, then rename for atomicity.
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(str(tmp), str(path))


# ---------- Subjects ----------

def load_subjects() -> list[Subject]:
    return [Subject.from_dict(d) for d in _load_json(SUBJECTS_FILE)]


def save_subjects(subjects: list[Subject]) -> None:
    _save_json(SUBJECTS_FILE, [s.to_dict() for s in subjects])


def get_subject(registration_no: str) -> Subject | None:
    for s in load_subjects():
        if s.registration_no == registration_no:
            return s
    return None


def upsert_subject(subject: Subject) -> None:
    subjects = load_subjects()
    for i, s in enumerate(subjects):
        if s.registration_no == subject.registration_no:
            subjects[i] = subject
            save_subjects(subjects)
            return
    subjects.append(subject)
    save_subjects(subjects)


def delete_subject(registration_no: str) -> bool:
    subjects = load_subjects()
    before = len(subjects)
    subjects = [s for s in subjects if s.registration_no != registration_no]
    if len(subjects) < before:
        save_subjects(subjects)
        return True
    return False


# ---------- Invoices ----------

def load_invoices() -> list[Invoice]:
    return [Invoice.from_dict(d) for d in _load_json(INVOICES_FILE)]


def save_invoices(invoices: list[Invoice]) -> None:
    _save_json(INVOICES_FILE, [i.to_dict() for i in invoices])


def get_invoice(invoice_number: str) -> Invoice | None:
    for inv in load_invoices():
        if inv.invoice_number == invoice_number:
            return inv
    return None


def upsert_invoice(invoice: Invoice) -> None:
    invoices = load_invoices()
    for i, inv in enumerate(invoices):
        if inv.invoice_number == invoice.invoice_number:
            invoices[i] = invoice
            save_invoices(invoices)
            return
    invoices.append(invoice)
    save_invoices(invoices)


def delete_invoice(invoice_number: str) -> bool:
    invoices = load_invoices()
    before = len(invoices)
    invoices = [i for i in invoices if i.invoice_number != invoice_number]
    if len(invoices) < before:
        save_invoices(invoices)
        return True
    return False


def next_invoice_number(year: int | None = None) -> str:
    """Generates the next sequential invoice number (YYYY-NNNN)."""
    if year is None:
        year = datetime.now().year
    prefix = str(year)
    invoices = load_invoices()
    max_seq = 0
    for inv in invoices:
        if inv.invoice_number.startswith(prefix + "-"):
            try:
                seq = int(inv.invoice_number.split("-")[1])
                max_seq = max(max_seq, seq)
            except (ValueError, IndexError):
                pass
    return f"{year}-{max_seq + 1:04d}"


# ---------- Recurring Templates ----------

def load_recurring() -> list[RecurringTemplate]:
    return [RecurringTemplate.from_dict(d) for d in _load_json(RECURRING_FILE)]


def save_recurring(templates: list[RecurringTemplate]) -> None:
    _save_json(RECURRING_FILE, [t.to_dict() for t in templates])


def upsert_recurring(template: RecurringTemplate) -> None:
    templates = load_recurring()
    for i, t in enumerate(templates):
        if t.template_name == template.template_name:
            templates[i] = template
            save_recurring(templates)
            return
    templates.append(template)
    save_recurring(templates)


# ---------- Tax Export Records ----------

def load_exports() -> list[TaxExportRecord]:
    return [TaxExportRecord.from_dict(d) for d in _load_json(EXPORTS_FILE)]


def save_exports(records: list[TaxExportRecord]) -> None:
    _save_json(EXPORTS_FILE, [r.to_dict() for r in records])


def add_export_record(record: TaxExportRecord) -> None:
    records = load_exports()
    records.append(record)
    save_exports(records)


# ---------- Exported files directory ----------

def get_exports_dir() -> Path:
    """Directory for exported PDFs, XMLs etc."""
    exports = DATA_DIR / "exports"
    exports.mkdir(exist_ok=True)
    return exports
