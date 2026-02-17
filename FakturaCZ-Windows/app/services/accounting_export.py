"""Accounting export service — ISDOC, Pohoda XML, with invoice locking."""

from datetime import date
from decimal import Decimal
from xml.sax.saxutils import escape as xml_escape

from app.models.invoice import Invoice
from app.models.tax_export import TaxExportRecord
from app.services import persistence
from app.services.vat import czech_round, breakdown


def _fmt_decimal(value: Decimal) -> str:
    return str(czech_round(value))


def _fmt_date_iso(d: str) -> str:
    return d  # Already ISO format


def generate_isdoc(invoice: Invoice) -> str:
    """Generate ISDOC 6.0.1 XML for a single invoice."""
    import uuid
    lines = invoice.get_lines()
    lines.sort(key=lambda l: l.sort_order)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="http://isdoc.cz/namespace/2013"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         version="6.0.1">
  <DocumentType>1</DocumentType>
  <ID>{xml_escape(invoice.invoice_number)}</ID>
  <UUID>{uuid.uuid4()}</UUID>
  <IssuingSystem>FakturaCZ 1.0</IssuingSystem>
  <IssueDate>{invoice.issued_date}</IssueDate>
  <TaxPointDate>{invoice.taxable_supply_date}</TaxPointDate>
  <Note>{xml_escape(invoice.note or '')}</Note>
  <LocalCurrencyCode>CZK</LocalCurrencyCode>"""

    subject = persistence.get_subject(invoice.subject_registration_no or "")
    if subject:
        xml += f"""
  <AccountingCustomerParty>
    <Party>
      <PartyIdentification>
        <ID>{xml_escape(subject.registration_no)}</ID>
      </PartyIdentification>
      <PartyName>
        <Name>{xml_escape(subject.name)}</Name>
      </PartyName>
      <PostalAddress>
        <StreetName>{xml_escape(subject.street)}</StreetName>
        <CityName>{xml_escape(subject.city)}</CityName>
        <PostalZone>{xml_escape(subject.zip)}</PostalZone>
        <Country>
          <IdentificationCode>CZ</IdentificationCode>
        </Country>
      </PostalAddress>"""
        if subject.vat_no:
            xml += f"""
      <PartyTaxScheme>
        <CompanyID>{xml_escape(subject.vat_no)}</CompanyID>
      </PartyTaxScheme>"""
        xml += """
    </Party>
  </AccountingCustomerParty>"""

    # Lines
    xml += "\n  <InvoiceLines>"
    for i, line in enumerate(lines):
        xml += f"""
    <InvoiceLine>
      <ID>{i + 1}</ID>
      <InvoicedQuantity unitCode="{xml_escape(line.unit)}">{_fmt_decimal(line.quantity)}</InvoicedQuantity>
      <LineExtensionAmount>{_fmt_decimal(line.line_total)}</LineExtensionAmount>
      <LineExtensionAmountTaxInclusive>{_fmt_decimal(line.line_total_with_vat)}</LineExtensionAmountTaxInclusive>
      <LineExtensionTaxAmount>{_fmt_decimal(line.vat_amount)}</LineExtensionTaxAmount>
      <UnitPrice>{_fmt_decimal(line.unit_price)}</UnitPrice>
      <ClassifiedTaxCategory>
        <Percent>{line.vat_rate_enum.value}</Percent>
      </ClassifiedTaxCategory>
      <Item>
        <Description>{xml_escape(line.item_description)}</Description>
      </Item>
    </InvoiceLine>"""
    xml += "\n  </InvoiceLines>"

    # Tax total
    bkdn = breakdown(lines)
    xml += "\n  <TaxTotal>"
    for rate, (base, vat) in bkdn.items():
        xml += f"""
    <TaxSubTotal>
      <TaxableAmount>{_fmt_decimal(base)}</TaxableAmount>
      <TaxAmount>{_fmt_decimal(vat)}</TaxAmount>
      <TaxCategory>
        <Percent>{rate.value}</Percent>
      </TaxCategory>
    </TaxSubTotal>"""
    xml += f"""
    <TaxAmount>{_fmt_decimal(invoice.total_vat)}</TaxAmount>
  </TaxTotal>
  <LegalMonetaryTotal>
    <TaxExclusiveAmount>{_fmt_decimal(invoice.subtotal)}</TaxExclusiveAmount>
    <TaxInclusiveAmount>{_fmt_decimal(invoice.total)}</TaxInclusiveAmount>
    <PayableAmount>{_fmt_decimal(invoice.total)}</PayableAmount>
  </LegalMonetaryTotal>
</Invoice>"""

    return xml


def generate_pohoda_xml(invoices: list[Invoice]) -> str:
    """Generate Pohoda-compatible XML for batch import."""
    xml = """<?xml version="1.0" encoding="Windows-1250"?>
<dat:dataPack
  xmlns:dat="http://www.stormware.cz/schema/version_2/data.xsd"
  xmlns:inv="http://www.stormware.cz/schema/version_2/invoice.xsd"
  xmlns:typ="http://www.stormware.cz/schema/version_2/type.xsd"
  id="FakturaCZ-export"
  application="FakturaCZ"
  version="2.0"
  note="Export z FakturaCZ">"""

    for inv in invoices:
        subject = persistence.get_subject(inv.subject_registration_no or "")
        lines = inv.get_lines()
        lines.sort(key=lambda l: l.sort_order)

        xml += f"""
  <dat:dataPackItem id="{xml_escape(inv.invoice_number)}" version="2.0">
    <inv:invoice version="2.0">
      <inv:invoiceHeader>
        <inv:invoiceType>issuedInvoice</inv:invoiceType>
        <inv:number>
          <typ:numberRequested>{xml_escape(inv.invoice_number)}</typ:numberRequested>
        </inv:number>
        <inv:symVar>{xml_escape(inv.variable_symbol or '')}</inv:symVar>
        <inv:date>{inv.issued_date}</inv:date>
        <inv:dateTax>{inv.taxable_supply_date}</inv:dateTax>
        <inv:dateDue>{inv.due_date}</inv:dateDue>"""

        if subject:
            xml += f"""
        <inv:partnerIdentity>
          <typ:address>
            <typ:company>{xml_escape(subject.name)}</typ:company>
            <typ:street>{xml_escape(subject.street)}</typ:street>
            <typ:city>{xml_escape(subject.city)}</typ:city>
            <typ:zip>{xml_escape(subject.zip)}</typ:zip>
            <typ:ico>{xml_escape(subject.registration_no)}</typ:ico>
            <typ:dic>{xml_escape(subject.vat_no or '')}</typ:dic>
          </typ:address>
        </inv:partnerIdentity>"""

        xml += """
      </inv:invoiceHeader>
      <inv:invoiceDetail>"""

        for line in lines:
            rate_label = "high" if line.vat_rate == "STANDARD" else ("low" if line.vat_rate == "REDUCED" else "none")
            xml += f"""
        <inv:invoiceItem>
          <inv:text>{xml_escape(line.item_description)}</inv:text>
          <inv:quantity>{_fmt_decimal(line.quantity)}</inv:quantity>
          <inv:unit>{xml_escape(line.unit)}</inv:unit>
          <inv:rateVAT>{rate_label}</inv:rateVAT>
          <inv:homeCurrency>
            <typ:unitPrice>{_fmt_decimal(line.unit_price)}</typ:unitPrice>
          </inv:homeCurrency>
        </inv:invoiceItem>"""

        xml += """
      </inv:invoiceDetail>
    </inv:invoice>
  </dat:dataPackItem>"""

    xml += "\n</dat:dataPack>"
    return xml


def perform_sharp_export(
    invoices: list[Invoice],
    export_type: str,
    year: int,
    month: int,
) -> TaxExportRecord:
    """
    Perform a 'sharp' accounting export: generate ISDOC for each invoice
    and lock them to prevent further modification.
    """
    exports_dir = persistence.get_exports_dir()
    invoice_ids = [inv.invoice_number for inv in invoices]

    # Generate and save ISDOC files
    for inv in invoices:
        xml = generate_isdoc(inv)
        path = exports_dir / f"{inv.invoice_number}_isdoc.xml"
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)

    # Lock all invoices
    all_invoices = persistence.load_invoices()
    for inv in all_invoices:
        if inv.invoice_number in invoice_ids:
            inv.is_locked = True
    persistence.save_invoices(all_invoices)

    # Record the export
    record = TaxExportRecord(
        export_type=export_type,
        period_year=year,
        period_month=month,
        is_sharp=True,
        invoice_ids=invoice_ids,
    )
    persistence.add_export_record(record)

    return record
