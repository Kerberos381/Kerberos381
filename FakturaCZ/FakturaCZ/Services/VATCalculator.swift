import Foundation

// MARK: - Czech Rounding

/// Czech rounding rules: mathematical rounding to 2 decimal places.
enum CzechRounding {
    /// Rounds a Decimal to 2 decimal places using banker's rounding (IEEE 754).
    static func round(_ value: Decimal) -> Decimal {
        var result = Decimal()
        var mutableValue = value
        NSDecimalRound(&result, &mutableValue, 2, .bankers)
        return result
    }
}

// MARK: - VAT Calculator

/// Centralized VAT calculation logic for invoices.
enum VATCalculator {

    /// Calculates the VAT amount for a single line.
    static func vatAmount(base: Decimal, rate: VATRate) -> Decimal {
        CzechRounding.round(base * rate.multiplier)
    }

    /// Calculates the total (base + VAT) for a single line.
    static func totalWithVAT(base: Decimal, rate: VATRate) -> Decimal {
        base + vatAmount(base: base, rate: rate)
    }

    /// Aggregates invoice lines into a VAT breakdown per rate.
    static func breakdown(for lines: [InvoiceLine]) -> [VATRate: VATBreakdownEntry] {
        var result: [VATRate: VATBreakdownEntry] = [:]

        for line in lines {
            let existing = result[line.vatRate] ?? VATBreakdownEntry(
                rate: line.vatRate, base: .zero, vat: .zero
            )
            result[line.vatRate] = VATBreakdownEntry(
                rate: line.vatRate,
                base: existing.base + line.lineTotal,
                vat: existing.vat + line.vatAmount
            )
        }

        return result
    }

    /// Computes the grand total across all lines with Czech rounding.
    static func grandTotal(for lines: [InvoiceLine]) -> Decimal {
        let subtotal = lines.reduce(Decimal.zero) { $0 + $1.lineTotal }
        let totalVAT = lines.reduce(Decimal.zero) { $0 + $1.vatAmount }
        return CzechRounding.round(subtotal + totalVAT)
    }
}

// MARK: - VAT Breakdown Entry

struct VATBreakdownEntry {
    let rate: VATRate
    let base: Decimal
    let vat: Decimal

    var total: Decimal { base + vat }
}
