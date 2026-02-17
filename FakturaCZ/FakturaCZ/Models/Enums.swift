import Foundation

// MARK: - VAT Rate

/// Czech VAT rates as defined by law.
enum VATRate: Int, Codable, CaseIterable, Identifiable {
    case zero = 0
    case reduced = 12
    case standard = 21

    var id: Int { rawValue }

    var label: String {
        switch self {
        case .zero: return "0 %"
        case .reduced: return "12 %"
        case .standard: return "21 %"
        }
    }

    var multiplier: Decimal {
        Decimal(rawValue) / 100
    }
}

// MARK: - Invoice State

/// Lifecycle states for an invoice document.
enum InvoiceState: String, Codable, CaseIterable, Identifiable {
    case open
    case sent
    case overdue
    case paid

    var id: String { rawValue }

    var label: String {
        switch self {
        case .open: return "Otevřená"
        case .sent: return "Odeslaná"
        case .overdue: return "Po splatnosti"
        case .paid: return "Zaplacená"
        }
    }

    var iconName: String {
        switch self {
        case .open: return "doc.badge.ellipsis"
        case .sent: return "paperplane"
        case .overdue: return "exclamationmark.triangle"
        case .paid: return "checkmark.circle"
        }
    }
}

// MARK: - Invoice Type

enum InvoiceType: String, Codable, CaseIterable, Identifiable {
    case standard
    case proforma
    case credit

    var id: String { rawValue }

    var label: String {
        switch self {
        case .standard: return "Faktura"
        case .proforma: return "Proforma"
        case .credit: return "Dobropis"
        }
    }
}

// MARK: - Recurrence Period

enum RecurrencePeriod: String, Codable, CaseIterable, Identifiable {
    case weekly
    case monthly
    case quarterly
    case yearly

    var id: String { rawValue }

    var label: String {
        switch self {
        case .weekly: return "Týdně"
        case .monthly: return "Měsíčně"
        case .quarterly: return "Čtvrtletně"
        case .yearly: return "Ročně"
        }
    }

    /// Returns the next occurrence date from a given date.
    func nextDate(from date: Date) -> Date {
        let calendar = Calendar.current
        switch self {
        case .weekly:
            return calendar.date(byAdding: .weekOfYear, value: 1, to: date)!
        case .monthly:
            return calendar.date(byAdding: .month, value: 1, to: date)!
        case .quarterly:
            return calendar.date(byAdding: .month, value: 3, to: date)!
        case .yearly:
            return calendar.date(byAdding: .year, value: 1, to: date)!
        }
    }
}

// MARK: - Supply Code (for reverse charge / OSS)

enum SupplyCode: String, Codable, CaseIterable, Identifiable {
    case domestic
    case reverseCharge
    case oss

    var id: String { rawValue }

    var label: String {
        switch self {
        case .domestic: return "Tuzemské plnění"
        case .reverseCharge: return "Přenesená daňová povinnost"
        case .oss: return "OSS (EU)"
        }
    }
}

// MARK: - Tax Period

enum TaxPeriod: String, Codable, CaseIterable, Identifiable {
    case monthly
    case quarterly

    var id: String { rawValue }

    var label: String {
        switch self {
        case .monthly: return "Měsíční"
        case .quarterly: return "Čtvrtletní"
        }
    }
}

// MARK: - KH Section (Kontrolní hlášení)

enum KHSection: String, Codable {
    case a4  // Issued invoices > 10,000 CZK with VAT ID
    case a5  // Issued invoices ≤ 10,000 CZK or without VAT ID
    case b2  // Received invoices > 10,000 CZK with VAT ID
    case b3  // Received invoices ≤ 10,000 CZK or without VAT ID
}
