import Foundation
import SwiftData

// MARK: - Tax Report Generator

/// Generates XML tax reports conforming to Czech Financial Administration schemas.
/// Handles both DPH (VAT return, DPHDP3) and KH (Control Statement, DPHKH1).
enum TaxReportGenerator {

    // MARK: - Taxable Supply Query

    /// Fetches invoices whose taxable_supply_date (DUZP) falls within the period.
    /// Excludes Proforma types and Draft states.
    @MainActor
    static func fetchTaxableInvoices(
        year: Int,
        month: Int,
        period: TaxPeriod = .monthly,
        context: ModelContext
    ) throws -> [Invoice] {
        let calendar = Calendar.current

        let startComponents: DateComponents
        let endComponents: DateComponents

        switch period {
        case .monthly:
            startComponents = DateComponents(year: year, month: month, day: 1)
            endComponents = DateComponents(year: year, month: month + 1, day: 1)
        case .quarterly:
            let quarterStart = ((month - 1) / 3) * 3 + 1
            startComponents = DateComponents(year: year, month: quarterStart, day: 1)
            endComponents = DateComponents(year: year, month: quarterStart + 3, day: 1)
        }

        guard let startDate = calendar.date(from: startComponents),
              let endDate = calendar.date(from: endComponents) else {
            return []
        }

        let proformaType = InvoiceType.proforma.rawValue
        let openState = InvoiceState.open.rawValue

        let predicate = #Predicate<Invoice> { invoice in
            invoice.taxableSupplyDate >= startDate &&
            invoice.taxableSupplyDate < endDate &&
            invoice.typeRaw != proformaType &&
            invoice.stateRaw != openState
        }

        let descriptor = FetchDescriptor<Invoice>(
            predicate: predicate,
            sortBy: [SortDescriptor(\Invoice.taxableSupplyDate)]
        )

        return try context.fetch(descriptor)
    }

    // MARK: - DPH XML (DPHDP3 Schema)

    /// Generates VAT return XML conforming to the DPHDP3 schema.
    static func generateDPHXML(
        invoices: [Invoice],
        taxpayerVATNo: String,
        year: Int,
        month: Int,
        period: TaxPeriod
    ) -> String {
        // Aggregate by VAT rate and supply code.
        var rateAggregates: [VATRate: (base: Decimal, vat: Decimal)] = [:]

        for invoice in invoices {
            for line in invoice.lines {
                let existing = rateAggregates[line.vatRate] ?? (base: .zero, vat: .zero)
                rateAggregates[line.vatRate] = (
                    base: existing.base + line.lineTotal,
                    vat: existing.vat + line.vatAmount
                )
            }
        }

        let totalBase = rateAggregates.values.reduce(Decimal.zero) { $0 + $1.base }
        let totalVAT = rateAggregates.values.reduce(Decimal.zero) { $0 + $1.vat }

        let periodCode = period == .monthly ? "M" : "Q"
        let periodValue = period == .monthly ? month : ((month - 1) / 3) + 1

        var xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <Pisemnost nazevSW="FakturaCZ" verzeSW="1.0">
          <DPHDP3 verzePis="02.01">
            <VetaD
              k_uladis="DPH"
              dokession="\(periodCode)"
              rok="\(year)"
              mesic="\(periodValue)"
              d_poddam="\(formatDateXML(Date()))"
              k_dar="\(taxpayerVATNo)"
            />
        """

        // Section 1: Standard rate (21%)
        if let std = rateAggregates[.standard] {
            xml += """

                <VetaR1
                  obrat23="\(formatDecimal(std.base))"
                  dan23="\(formatDecimal(std.vat))"
                />
            """
        }

        // Section 2: Reduced rate (12%)
        if let red = rateAggregates[.reduced] {
            xml += """

                <VetaR2
                  obrat5="\(formatDecimal(red.base))"
                  dan5="\(formatDecimal(red.vat))"
                />
            """
        }

        // Summary section
        xml += """

            <VetaR6
              dano_da="\(formatDecimal(totalVAT))"
              dano_no="\(formatDecimal(totalBase))"
            />
          </DPHDP3>
        </Pisemnost>
        """

        return xml
    }

    // MARK: - KH XML (DPHKH1 Schema — Control Statement)

    /// Generates Control Statement XML conforming to the DPHKH1 schema.
    static func generateKHXML(
        invoices: [Invoice],
        taxpayerVATNo: String,
        year: Int,
        month: Int
    ) -> String {
        // Classify invoices into KH sections.
        var sectionA4: [Invoice] = []  // Issued, > 10,000 CZK, counterparty has DIČ
        var sectionA5: [Invoice] = []  // Issued, ≤ 10,000 CZK or no DIČ

        for invoice in invoices {
            let total = invoice.total
            let hasVATNo = invoice.subject?.isVATPayer ?? false

            if total > 10_000 && hasVATNo {
                sectionA4.append(invoice)
            } else {
                sectionA5.append(invoice)
            }
        }

        var xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <Pisemnost nazevSW="FakturaCZ" verzeSW="1.0">
          <DPHKH1 verzePis="02.01">
            <VetaD
              k_uladis="KH"
              rok="\(year)"
              mesic="\(month)"
              d_poddam="\(formatDateXML(Date()))"
              k_dar="\(taxpayerVATNo)"
            />
        """

        // Section A.4 — Issued invoices > 10,000 CZK with VAT ID
        if !sectionA4.isEmpty {
            xml += "\n    <!-- Section A.4: Issued invoices > 10,000 CZK -->"
            for invoice in sectionA4 {
                let breakdown = VATCalculator.breakdown(for: invoice.lines)
                for (rate, entry) in breakdown where rate != .zero {
                    xml += """

                    <VetaA4
                      c_evid_dd="\(escapeXML(invoice.invoiceNumber))"
                      dic_odb="\(escapeXML(invoice.subject?.vatNo ?? ""))"
                      duzp="\(formatDateXML(invoice.taxableSupplyDate))"
                      zakl_dane\(rate == .standard ? "1" : "2")="\(formatDecimal(entry.base))"
                      dan\(rate == .standard ? "1" : "2")="\(formatDecimal(entry.vat))"
                    />
                    """
                }
            }
        }

        // Section A.5 — Aggregated totals for smaller invoices
        if !sectionA5.isEmpty {
            var totalBase21: Decimal = .zero
            var totalVAT21: Decimal = .zero
            var totalBase12: Decimal = .zero
            var totalVAT12: Decimal = .zero

            for invoice in sectionA5 {
                let breakdown = VATCalculator.breakdown(for: invoice.lines)
                if let std = breakdown[.standard] {
                    totalBase21 += std.base
                    totalVAT21 += std.vat
                }
                if let red = breakdown[.reduced] {
                    totalBase12 += red.base
                    totalVAT12 += red.vat
                }
            }

            xml += """

                <!-- Section A.5: Aggregated small invoices -->
                <VetaA5
                  zakl_dane1="\(formatDecimal(totalBase21))"
                  dan1="\(formatDecimal(totalVAT21))"
                  zakl_dane2="\(formatDecimal(totalBase12))"
                  dan2="\(formatDecimal(totalVAT12))"
                />
            """
        }

        xml += """

          </DPHKH1>
        </Pisemnost>
        """

        return xml
    }

    // MARK: - Helpers

    private static func formatDecimal(_ value: Decimal) -> String {
        let rounded = CzechRounding.round(value)
        return NSDecimalNumber(decimal: rounded).stringValue
    }

    private static func formatDateXML(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd.MM.yyyy"
        formatter.locale = Locale(identifier: "cs_CZ")
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
