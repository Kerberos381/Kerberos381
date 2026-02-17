import Foundation
import SwiftData

/// An invoice document with child line items.
@Model
final class Invoice {
    // MARK: - Identifiers

    /// Sequential invoice number (e.g., "2026-0001").
    @Attribute(.unique)
    var invoiceNumber: String

    // MARK: - Type & State

    var typeRaw: String
    var stateRaw: String

    var type: InvoiceType {
        get { InvoiceType(rawValue: typeRaw) ?? .standard }
        set { typeRaw = newValue.rawValue }
    }

    var state: InvoiceState {
        get { InvoiceState(rawValue: stateRaw) ?? .open }
        set { stateRaw = newValue.rawValue }
    }

    // MARK: - Dates

    /// Date the invoice was issued.
    var issuedDate: Date

    /// Date of taxable supply (DUZP) — the tax point binding for the state.
    var taxableSupplyDate: Date

    /// Payment due date.
    var dueDate: Date

    // MARK: - Payment

    var variableSymbol: String?
    var bankAccount: String?
    var iban: String?
    var paymentMethod: String?

    // MARK: - Supply classification

    var supplyCodeRaw: String

    var supplyCode: SupplyCode {
        get { SupplyCode(rawValue: supplyCodeRaw) ?? .domestic }
        set { supplyCodeRaw = newValue.rawValue }
    }

    // MARK: - Notes

    var note: String?
    var footerText: String?

    // MARK: - Locking (for accounting export immutability)

    /// When true, the invoice rejects modifications to preserve data integrity
    /// between Fakturoid and external accounting software.
    var isLocked: Bool

    // MARK: - Metadata

    var createdAt: Date
    var updatedAt: Date

    // MARK: - Relationships

    var subject: Subject?

    @Relationship(deleteRule: .cascade, inverse: \InvoiceLine.invoice)
    var lines: [InvoiceLine] = []

    // MARK: - Computed Totals

    /// Sum of all line totals before VAT.
    var subtotal: Decimal {
        lines.reduce(Decimal.zero) { $0 + $1.lineTotal }
    }

    /// Sum of all VAT amounts.
    var totalVAT: Decimal {
        lines.reduce(Decimal.zero) { $0 + $1.vatAmount }
    }

    /// Grand total including VAT, with Czech rounding applied.
    var total: Decimal {
        CzechRounding.round(subtotal + totalVAT)
    }

    /// Remaining amount to be paid (for partial payment support).
    var remainingAmount: Decimal {
        total // Extend with payment tracking if needed.
    }

    /// Groups lines by VAT rate and returns aggregated base + VAT per rate.
    var vatBreakdown: [VATRate: (base: Decimal, vat: Decimal)] {
        var result: [VATRate: (base: Decimal, vat: Decimal)] = [:]
        for line in lines {
            let existing = result[line.vatRate] ?? (base: .zero, vat: .zero)
            result[line.vatRate] = (
                base: existing.base + line.lineTotal,
                vat: existing.vat + line.vatAmount
            )
        }
        return result
    }

    // MARK: - State Machine

    /// Whether the invoice is overdue (current_date > due_date AND not paid).
    var isOverdue: Bool {
        state != .paid && Date() > dueDate && remainingAmount > 0
    }

    /// Transition to the next valid state. Returns false if transition is invalid.
    @discardableResult
    func transition(to newState: InvoiceState) -> Bool {
        guard canTransition(to: newState) else { return false }
        state = newState
        updatedAt = Date()
        return true
    }

    func canTransition(to newState: InvoiceState) -> Bool {
        switch (state, newState) {
        case (.open, .sent), (.open, .paid):
            return true
        case (.sent, .overdue), (.sent, .paid):
            return true
        case (.overdue, .paid):
            return true
        default:
            return false
        }
    }

    // MARK: - Locking Guard

    /// Returns true if modification is allowed.
    var isEditable: Bool {
        !isLocked && state == .open
    }

    // MARK: - Init

    init(
        invoiceNumber: String,
        type: InvoiceType = .standard,
        issuedDate: Date = Date(),
        taxableSupplyDate: Date = Date(),
        dueDate: Date = Calendar.current.date(byAdding: .day, value: 14, to: Date())!,
        supplyCode: SupplyCode = .domestic,
        variableSymbol: String? = nil,
        note: String? = nil
    ) {
        self.invoiceNumber = invoiceNumber
        self.typeRaw = type.rawValue
        self.stateRaw = InvoiceState.open.rawValue
        self.issuedDate = issuedDate
        self.taxableSupplyDate = taxableSupplyDate
        self.dueDate = dueDate
        self.supplyCodeRaw = supplyCode.rawValue
        self.variableSymbol = variableSymbol
        self.note = note
        self.isLocked = false
        self.createdAt = Date()
        self.updatedAt = Date()
    }
}
