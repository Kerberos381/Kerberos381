import Foundation
import SwiftData

/// A recurring invoice template that generates new invoices on a schedule.
@Model
final class RecurringTemplate {
    // MARK: - Template Info

    var templateName: String

    // MARK: - Schedule

    var periodRaw: String
    var startDate: Date
    var nextOccurrenceDate: Date
    var endDate: Date?
    var isActive: Bool

    var period: RecurrencePeriod {
        get { RecurrencePeriod(rawValue: periodRaw) ?? .monthly }
        set { periodRaw = newValue.rawValue }
    }

    // MARK: - Invoice Template Attributes

    /// Text for invoice lines, may contain placeholders like {month}, {year}.
    var lineDescriptionTemplate: String
    var defaultNote: String?
    var paymentTermDays: Int
    var supplyCodeRaw: String

    var supplyCode: SupplyCode {
        get { SupplyCode(rawValue: supplyCodeRaw) ?? .domestic }
        set { supplyCodeRaw = newValue.rawValue }
    }

    // MARK: - Line Items Template

    /// Stored as JSON-encoded array of line item specs.
    var lineItemsJSON: Data?

    // MARK: - Relationship

    var subject: Subject?

    // MARK: - Metadata

    var createdAt: Date
    var lastGeneratedAt: Date?

    // MARK: - Init

    init(
        templateName: String,
        period: RecurrencePeriod = .monthly,
        startDate: Date = Date(),
        paymentTermDays: Int = 14,
        lineDescriptionTemplate: String = "",
        supplyCode: SupplyCode = .domestic
    ) {
        self.templateName = templateName
        self.periodRaw = period.rawValue
        self.startDate = startDate
        self.nextOccurrenceDate = startDate
        self.endDate = nil
        self.isActive = true
        self.lineDescriptionTemplate = lineDescriptionTemplate
        self.paymentTermDays = paymentTermDays
        self.supplyCodeRaw = supplyCode.rawValue
        self.createdAt = Date()
    }

    // MARK: - Placeholder Resolution

    /// Resolves placeholders in the template text for a given date.
    func resolveDescription(for date: Date) -> String {
        let calendar = Calendar.current
        let month = calendar.component(.month, from: date)
        let year = calendar.component(.year, from: date)

        let czechMonths = [
            "leden", "únor", "březen", "duben", "květen", "červen",
            "červenec", "srpen", "září", "říjen", "listopad", "prosinec"
        ]

        return lineDescriptionTemplate
            .replacingOccurrences(of: "{month}", with: czechMonths[month - 1])
            .replacingOccurrences(of: "{month_num}", with: String(month))
            .replacingOccurrences(of: "{year}", with: String(year))
    }

    /// Advances the schedule to the next occurrence.
    func advance() {
        nextOccurrenceDate = period.nextDate(from: nextOccurrenceDate)
        lastGeneratedAt = Date()

        if let end = endDate, nextOccurrenceDate > end {
            isActive = false
        }
    }

    /// Whether generation is due today.
    var isDueToday: Bool {
        guard isActive else { return false }
        return Calendar.current.isDateInToday(nextOccurrenceDate)
    }
}

// MARK: - Line Item Spec (for template serialization)

struct LineItemSpec: Codable {
    let description: String
    let quantity: Decimal
    let unitPrice: Decimal
    let vatRate: Int
    let unit: String
}
