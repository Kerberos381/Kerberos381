"""Tax report XML serialization — DPH (DPHDP3) and KH (DPHKH1) schemas."""

from datetime import date, datetime
from decimal import Decimal
from xml.sax.saxutils import escape as xml_escape

from app.models.enums import InvoiceState, InvoiceType, TaxPeriod, VATRate
from app.models.invoice import Invoice
from app.services import persistence
from app.services.vat import czech_round, breakdown


def fetch_taxable_invoices(
    year: int,
    month: int,
    period: TaxPeriod = TaxPeriod.MONTHLY,
) -> list[Invoice]:
    """
    Fetch invoices whose taxable_supply_date (DUZP) falls within the period.
    Excludes Proforma types and Draft/Open states.
    """
    if period == TaxPeriod.MONTHLY:
        start_month = month
        end_month = month + 1
        end_year = year
        if end_month > 12:
            end_month = 1
            end_year = year + 1
    else:
        quarter_start = ((month - 1) // 3) * 3 + 1
        start_month = quarter_start
        end_month = quarter_start + 3
        end_year = year
        if end_month > 12:
            end_month = end_month - 12
            end_year = year + 1

    start_date = date(year, start_month, 1)
    end_date = date(end_year, end_month, 1)

    invoices = persistence.load_invoices()
    result = []
    for inv in invoices:
        duzp = date.fromisoformat(inv.taxable_supply_date)
        if duzp < start_date or duzp >= end_date:
            continue
        if inv.type == InvoiceType.PROFORMA.name:
            continue
        if inv.state == InvoiceState.OPEN.name:
            continue
        result.append(inv)

    result.sort(key=lambda i: i.taxable_supply_date)
    return result


def _fmt_decimal(value: Decimal) -> str:
    return str(czech_round(value))


def _fmt_date(d: date | str) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d.strftime("%d.%m.%Y")


def generate_dph_xml(
    invoices: list[Invoice],
    taxpayer_vat_no: str,
    year: int,
    month: int,
    period: TaxPeriod,
) -> str:
    """Generate VAT return XML conforming to DPHDP3 schema."""
    rate_agg: dict[VATRate, tuple[Decimal, Decimal]] = {}
    for inv in invoices:
        for rate, (base, vat) in inv.vat_breakdown.items():
            existing_base, existing_vat = rate_agg.get(rate, (Decimal("0"), Decimal("0")))
            rate_agg[rate] = (existing_base + base, existing_vat + vat)

    total_base = sum(v[0] for v in rate_agg.values())
    total_vat = sum(v[1] for v in rate_agg.values())

    period_code = "M" if period == TaxPeriod.MONTHLY else "Q"
    period_val = month if period == TaxPeriod.MONTHLY else ((month - 1) // 3) + 1

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Pisemnost nazevSW="FakturaCZ" verzeSW="1.0">
  <DPHDP3 verzePis="02.01">
    <VetaD
      k_uladis="DPH"
      dokession="{period_code}"
      rok="{year}"
      mesic="{period_val}"
      d_poddam="{_fmt_date(date.today())}"
      k_dar="{xml_escape(taxpayer_vat_no)}"
    />"""

    if VATRate.STANDARD in rate_agg:
        base, vat = rate_agg[VATRate.STANDARD]
        xml += f"""
    <VetaR1
      obrat23="{_fmt_decimal(base)}"
      dan23="{_fmt_decimal(vat)}"
    />"""

    if VATRate.REDUCED in rate_agg:
        base, vat = rate_agg[VATRate.REDUCED]
        xml += f"""
    <VetaR2
      obrat5="{_fmt_decimal(base)}"
      dan5="{_fmt_decimal(vat)}"
    />"""

    xml += f"""
    <VetaR6
      dano_da="{_fmt_decimal(total_vat)}"
      dano_no="{_fmt_decimal(total_base)}"
    />
  </DPHDP3>
</Pisemnost>"""

    return xml


def generate_kh_xml(
    invoices: list[Invoice],
    taxpayer_vat_no: str,
    year: int,
    month: int,
) -> str:
    """Generate Control Statement XML conforming to DPHKH1 schema."""
    section_a4: list[Invoice] = []
    section_a5: list[Invoice] = []

    for inv in invoices:
        total = inv.total
        subject = persistence.get_subject(inv.subject_registration_no or "")
        has_vat = subject and subject.is_vat_payer

        if total > 10_000 and has_vat:
            section_a4.append(inv)
        else:
            section_a5.append(inv)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Pisemnost nazevSW="FakturaCZ" verzeSW="1.0">
  <DPHKH1 verzePis="02.01">
    <VetaD
      k_uladis="KH"
      rok="{year}"
      mesic="{month}"
      d_poddam="{_fmt_date(date.today())}"
      k_dar="{xml_escape(taxpayer_vat_no)}"
    />"""

    # Section A.4
    if section_a4:
        xml += "\n    <!-- Section A.4: Issued invoices > 10,000 CZK -->"
        for inv in section_a4:
            subject = persistence.get_subject(inv.subject_registration_no or "")
            vat_no = subject.vat_no if subject else ""
            for rate, (base, vat) in inv.vat_breakdown.items():
                if rate == VATRate.ZERO:
                    continue
                col = "1" if rate == VATRate.STANDARD else "2"
                xml += f"""
    <VetaA4
      c_evid_dd="{xml_escape(inv.invoice_number)}"
      dic_odb="{xml_escape(vat_no or '')}"
      duzp="{_fmt_date(inv.taxable_supply_date)}"
      zakl_dane{col}="{_fmt_decimal(base)}"
      dan{col}="{_fmt_decimal(vat)}"
    />"""

    # Section A.5
    if section_a5:
        total_base21 = total_vat21 = Decimal("0")
        total_base12 = total_vat12 = Decimal("0")

        for inv in section_a5:
            for rate, (base, vat) in inv.vat_breakdown.items():
                if rate == VATRate.STANDARD:
                    total_base21 += base
                    total_vat21 += vat
                elif rate == VATRate.REDUCED:
                    total_base12 += base
                    total_vat12 += vat

        xml += f"""
    <!-- Section A.5: Aggregated small invoices -->
    <VetaA5
      zakl_dane1="{_fmt_decimal(total_base21)}"
      dan1="{_fmt_decimal(total_vat21)}"
      zakl_dane2="{_fmt_decimal(total_base12)}"
      dan2="{_fmt_decimal(total_vat12)}"
    />"""

    xml += """
  </DPHKH1>
</Pisemnost>"""

    return xml
