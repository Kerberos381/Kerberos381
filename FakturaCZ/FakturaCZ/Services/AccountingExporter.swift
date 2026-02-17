import Foundation
import SwiftData

// MARK: - Accounting Exporter

/// ETL service for generating accounting exports (ISDOC/Pohoda) and enforcing immutability.
enum AccountingExporter {

    // MARK: - ISDOC Export

    /// Generates an ISDOC XML document for a single invoice.
    static func generateISDOC(invoice: Invoice) -> String {
        let lines = invoice.lines.sorted { $0.sortOrder < $1.sortOrder }

        var xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="http://isdoc.cz/namespace/2013"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 version="6.0.1">
          <DocumentType>1</DocumentType>
          <ID>\(escapeXML(invoice.invoiceNumber))</ID>
          <UUID>\(UUID().uuidString)</UUID>
          <IssuingSystem>FakturaCZ 1.0</IssuingSystem>
          <IssueDate>\(formatDateISO(invoice.issuedDate))</IssueDate>
          <TaxPointDate>\(formatDateISO(invoice.taxableSupplyDate))</TaxPointDate>
          <Note>\(escapeXML(invoice.note ?? ""))</Note>
          <LocalCurrencyCode>CZK</LocalCurrencyCode>
        """

        // Supplier info would come from app settings (the user's own company).
        // Buyer info from the subject.
        if let subject = invoice.subject {
            xml += """

              <AccountingSupplierParty>
                <!-- Populated from app settings -->
              </AccountingSupplierParty>
              <AccountingCustomerParty>
                <Party>
                  <PartyIdentification>
                    <ID>\(escapeXML(subject.registrationNo))</ID>
                  </PartyIdentification>
                  <PartyName>
                    <Name>\(escapeXML(subject.name))</Name>
                  </PartyName>
                  <PostalAddress>
                    <StreetName>\(escapeXML(subject.street))</StreetName>
                    <CityName>\(escapeXML(subject.city))</CityName>
                    <PostalZone>\(escapeXML(subject.zip))</PostalZone>
                    <Country>
                      <IdentificationCode>CZ</IdentificationCode>
                    </Country>
                  </PostalAddress>
            """
            if let vatNo = subject.vatNo {
                xml += """

                      <PartyTaxScheme>
                        <CompanyID>\(escapeXML(vatNo))</CompanyID>
                      </PartyTaxScheme>
                """
            }
            xml += """

                </Party>
              </AccountingCustomerParty>
            """
        }

        // Invoice lines
        xml += "\n  <InvoiceLines>"
        for (index, line) in lines.enumerated() {
            xml += """

                <InvoiceLine>
                  <ID>\(index + 1)</ID>
                  <InvoicedQuantity unitCode="\(escapeXML(line.unit))">\(formatDecimal(line.quantity))</InvoicedQuantity>
                  <LineExtensionAmount>\(formatDecimal(line.lineTotal))</LineExtensionAmount>
                  <LineExtensionAmountTaxInclusive>\(formatDecimal(line.lineTotalWithVAT))</LineExtensionAmountTaxInclusive>
                  <LineExtensionTaxAmount>\(formatDecimal(line.vatAmount))</LineExtensionTaxAmount>
                  <UnitPrice>\(formatDecimal(line.unitPrice))</UnitPrice>
                  <ClassifiedTaxCategory>
                    <Percent>\(line.vatRate.rawValue)</Percent>
                    <VATCalculationMethod>0</VATCalculationMethod>
                  </ClassifiedTaxCategory>
                  <Item>
                    <Description>\(escapeXML(line.itemDescription))</Description>
                  </Item>
                </InvoiceLine>
            """
        }
        xml += "\n  </InvoiceLines>"

        // Tax total
        let breakdown = VATCalculator.breakdown(for: lines)
        xml += "\n  <TaxTotal>"
        for (rate, entry) in breakdown {
            xml += """

              <TaxSubTotal>
                <TaxableAmount>\(formatDecimal(entry.base))</TaxableAmount>
                <TaxAmount>\(formatDecimal(entry.vat))</TaxAmount>
                <TaxCategory>
                  <Percent>\(rate.rawValue)</Percent>
                </TaxCategory>
              </TaxSubTotal>
            """
        }
        xml += """

            <TaxAmount>\(formatDecimal(invoice.totalVAT))</TaxAmount>
          </TaxTotal>
          <LegalMonetaryTotal>
            <TaxExclusiveAmount>\(formatDecimal(invoice.subtotal))</TaxExclusiveAmount>
            <TaxInclusiveAmount>\(formatDecimal(invoice.total))</TaxInclusiveAmount>
            <PayableAmount>\(formatDecimal(invoice.total))</PayableAmount>
          </LegalMonetaryTotal>
        </Invoice>
        """

        return xml
    }

    // MARK: - Sharp Export with Locking

    /// Performs a "sharp" accounting export, generating ISDOC for each invoice
    /// and locking them to prevent further modification.
    @MainActor
    static func performSharpExport(
        invoices: [Invoice],
        exportType: String,
        year: Int,
        month: Int,
        context: ModelContext
    ) throws -> TaxExportRecord {
        // Generate ISDOC for each invoice.
        var exports: [(invoice: Invoice, xml: String)] = []
        for invoice in invoices {
            let xml = generateISDOC(invoice: invoice)
            exports.append((invoice, xml))
        }

        // Lock all invoices — they now reject PATCH/PUT modifications.
        let invoiceIDs = invoices.map(\.invoiceNumber)
        for invoice in invoices {
            invoice.isLocked = true
            invoice.updatedAt = Date()
        }

        // Create the export record.
        let record = TaxExportRecord(
            exportType: exportType,
            periodYear: year,
            periodMonth: month,
            isSharp: true,
            invoiceIDs: invoiceIDs
        )

        context.insert(record)
        try context.save()

        return record
    }

    // MARK: - Pohoda XML Export

    /// Generates a simplified Pohoda-compatible XML for import.
    static func generatePohodaXML(invoices: [Invoice]) -> String {
        var xml = """
        <?xml version="1.0" encoding="Windows-1250"?>
        <dat:dataPack
          xmlns:dat="http://www.stormware.cz/schema/version_2/data.xsd"
          xmlns:inv="http://www.stormware.cz/schema/version_2/invoice.xsd"
          xmlns:typ="http://www.stormware.cz/schema/version_2/type.xsd"
          id="FakturaCZ-export"
          ico=""
          application="FakturaCZ"
          version="2.0"
          note="Export z FakturaCZ">
        """

        for invoice in invoices {
            xml += """

          <dat:dataPackItem id="\(escapeXML(invoice.invoiceNumber))" version="2.0">
            <inv:invoice version="2.0">
              <inv:invoiceHeader>
                <inv:invoiceType>issuedInvoice</inv:invoiceType>
                <inv:number>
                  <typ:numberRequested>\(escapeXML(invoice.invoiceNumber))</typ:numberRequested>
                </inv:number>
                <inv:symVar>\(escapeXML(invoice.variableSymbol ?? ""))</inv:symVar>
                <inv:date>\(formatDateISO(invoice.issuedDate))</inv:date>
                <inv:dateTax>\(formatDateISO(invoice.taxableSupplyDate))</inv:dateTax>
                <inv:dateDue>\(formatDateISO(invoice.dueDate))</inv:dateDue>
            """

            if let subject = invoice.subject {
                xml += """

                    <inv:partnerIdentity>
                      <typ:address>
                        <typ:company>\(escapeXML(subject.name))</typ:company>
                        <typ:street>\(escapeXML(subject.street))</typ:street>
                        <typ:city>\(escapeXML(subject.city))</typ:city>
                        <typ:zip>\(escapeXML(subject.zip))</typ:zip>
                        <typ:ico>\(escapeXML(subject.registrationNo))</typ:ico>
                        <typ:dic>\(escapeXML(subject.vatNo ?? ""))</typ:dic>
                      </typ:address>
                    </inv:partnerIdentity>
                """
            }

            xml += """

                  </inv:invoiceHeader>
                  <inv:invoiceDetail>
            """

            for line in invoice.lines.sorted(by: { $0.sortOrder < $1.sortOrder }) {
                xml += """

                    <inv:invoiceItem>
                      <inv:text>\(escapeXML(line.itemDescription))</inv:text>
                      <inv:quantity>\(formatDecimal(line.quantity))</inv:quantity>
                      <inv:unit>\(escapeXML(line.unit))</inv:unit>
                      <inv:rateVAT>\(line.vatRate == .standard ? "high" : line.vatRate == .reduced ? "low" : "none")</inv:rateVAT>
                      <inv:homeCurrency>
                        <typ:unitPrice>\(formatDecimal(line.unitPrice))</typ:unitPrice>
                      </inv:homeCurrency>
                    </inv:invoiceItem>
                """
            }

            xml += """

                  </inv:invoiceDetail>
                </inv:invoice>
              </dat:dataPackItem>
            """
        }

        xml += "\n</dat:dataPack>"
        return xml
    }

    // MARK: - Helpers

    private static func formatDecimal(_ value: Decimal) -> String {
        NSDecimalNumber(decimal: CzechRounding.round(value)).stringValue
    }

    private static func formatDateISO(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    private static func escapeXML(_ string: String) -> String {
        string
            .replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
            .replacingOccurrences(of: "\"", with: "&quot;")
            .replacingOccurrences(of: "'", with: "&apos;")
    }
}
