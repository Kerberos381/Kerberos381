"""PDF invoice renderer using ReportLab."""

from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT

from app.models.invoice import Invoice
from app.services import persistence
from app.services.vat import czech_round, breakdown


def _fmt_currency(value: Decimal) -> str:
    rounded = czech_round(value)
    # Format with Czech locale style
    s = f"{rounded:,.2f}"
    s = s.replace(",", " ").replace(".", ",")
    return f"{s} Kč"


def _fmt_number(value: Decimal) -> str:
    return str(value)


def _fmt_date(iso_date: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso_date)
    return d.strftime("%d.%m.%Y")


def render_invoice(invoice: Invoice, output_path: Path) -> Path:
    """Render an invoice to PDF and return the output path."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "Title2", parent=styles["Title"], fontSize=20, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        "RightAligned", parent=styles["Normal"], alignment=TA_RIGHT
    ))
    styles.add(ParagraphStyle(
        "SmallGray", parent=styles["Normal"], fontSize=8, textColor=colors.gray
    ))
    styles.add(ParagraphStyle(
        "BoldRight", parent=styles["Normal"], alignment=TA_RIGHT,
        fontSize=14, fontName="Helvetica-Bold"
    ))

    story = []
    lines = invoice.get_lines()
    lines.sort(key=lambda l: l.sort_order)
    subject = persistence.get_subject(invoice.subject_registration_no or "")

    # -- Header --
    from app.models.enums import InvoiceType, InvoiceState
    type_label = InvoiceType[invoice.type].label.upper()
    state_label = InvoiceState[invoice.state].label

    story.append(Paragraph(f"{type_label} č. {invoice.invoice_number}", styles["Title2"]))
    story.append(Paragraph(f"Stav: {state_label}", styles["SmallGray"]))
    story.append(Spacer(1, 4 * mm))

    if invoice.is_locked:
        story.append(Paragraph(
            "🔒 Faktura je uzamčena pro účetní export",
            ParagraphStyle("Locked", parent=styles["Normal"],
                           fontSize=9, textColor=colors.HexColor("#D97706"))
        ))
        story.append(Spacer(1, 2 * mm))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
    story.append(Spacer(1, 4 * mm))

    # -- Dates --
    date_data = [
        ["Datum vystavení:", _fmt_date(invoice.issued_date)],
        ["DUZP:", _fmt_date(invoice.taxable_supply_date)],
        ["Datum splatnosti:", _fmt_date(invoice.due_date)],
    ]
    date_table = Table(date_data, colWidths=[120, 200])
    date_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(date_table)
    story.append(Spacer(1, 4 * mm))

    # -- Subject --
    if subject:
        story.append(Paragraph("Odběratel:", styles["Heading4"]))
        story.append(Paragraph(subject.name, ParagraphStyle(
            "SubjectName", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10
        )))
        story.append(Paragraph(subject.street, styles["Normal"]))
        story.append(Paragraph(f"{subject.zip} {subject.city}", styles["Normal"]))
        story.append(Paragraph(f"IČO: {subject.registration_no}", styles["Normal"]))
        if subject.vat_no:
            story.append(Paragraph(f"DIČ: {subject.vat_no}", styles["Normal"]))
        story.append(Spacer(1, 4 * mm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray))
    story.append(Spacer(1, 4 * mm))

    # -- Line Items Table --
    table_data = [["Popis", "Množství", "Jedn.", "Cena/ks", "DPH", "Celkem"]]
    for line in lines:
        table_data.append([
            line.item_description,
            _fmt_number(line.quantity),
            line.unit,
            _fmt_currency(line.unit_price),
            line.vat_rate_enum.label,
            _fmt_currency(line.line_total_with_vat),
        ])

    col_widths = [180, 50, 35, 80, 40, 80]
    line_table = Table(table_data, colWidths=col_widths)
    line_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 4 * mm))

    # -- VAT Breakdown --
    bkdn = breakdown(lines)
    if bkdn:
        vat_data = [["Sazba DPH", "Základ", "DPH"]]
        for rate in sorted(bkdn, key=lambda r: r.value, reverse=True):
            base, vat = bkdn[rate]
            vat_data.append([rate.label, _fmt_currency(base), _fmt_currency(vat)])

        vat_table = Table(vat_data, colWidths=[80, 100, 100])
        vat_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(vat_table)
        story.append(Spacer(1, 4 * mm))

    # -- Total --
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 2 * mm))
    total_data = [[
        Paragraph("Celkem k úhradě:", styles["Normal"]),
        Paragraph(_fmt_currency(invoice.total), styles["BoldRight"]),
    ]]
    total_table = Table(total_data, colWidths=[300, 165])
    story.append(total_table)
    story.append(Spacer(1, 4 * mm))

    # -- Payment Info --
    if invoice.variable_symbol or invoice.bank_account:
        story.append(Paragraph("Platební údaje:", styles["Heading4"]))
        if invoice.variable_symbol:
            story.append(Paragraph(f"Variabilní symbol: {invoice.variable_symbol}", styles["Normal"]))
        if invoice.bank_account:
            story.append(Paragraph(f"Číslo účtu: {invoice.bank_account}", styles["Normal"]))
        story.append(Spacer(1, 4 * mm))

    # -- Note --
    if invoice.note:
        story.append(Paragraph("Poznámka:", styles["Heading4"]))
        story.append(Paragraph(invoice.note, styles["Normal"]))

    doc.build(story)
    return output_path
