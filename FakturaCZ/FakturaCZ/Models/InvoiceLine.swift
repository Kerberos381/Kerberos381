import Foundation
import SwiftData

/// A single line item on an invoice.
@Model
final class InvoiceLine {
    // MARK: - Description

    var itemDescription: String

    // MARK: - Amounts

    var quantity: Decimal
    var unitPrice: Decimal

    // MARK: - VAT

    var vatRateRaw: Int

    var vatRate: VATRate {
        get { VATRate(rawValue: vatRateRaw) ?? .standard }
        set { vatRateRaw = newValue.rawValue }
    }

    // MARK: - Unit

    var unit: String

    // MARK: - Computed

    /// Line Total = quantity × unit_price
    var lineTotal: Decimal {
        quantity * unitPrice
    }

    /// VAT amount for this line.
    var vatAmount: Decimal {
        lineTotal * vatRate.multiplier
    }

    /// Line total including VAT.
    var lineTotalWithVAT: Decimal {
        lineTotal + vatAmount
    }

    // MARK: - Relationship

    var invoice: Invoice?

    // MARK: - Ordering

    var sortOrder: Int

    // MARK: - Init

    init(
        itemDescription: String,
        quantity: Decimal = 1,
        unitPrice: Decimal,
        vatRate: VATRate = .standard,
        unit: String = "ks",
        sortOrder: Int = 0
    ) {
        self.itemDescription = itemDescription
        self.quantity = quantity
        self.unitPrice = unitPrice
        self.vatRateRaw = vatRate.rawValue
        self.unit = unit
        self.sortOrder = sortOrder
    }
}
