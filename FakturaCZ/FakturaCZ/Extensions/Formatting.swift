import Foundation
import SwiftData

/// Formatting extensions used across the app.
extension Decimal {
    /// Formats as Czech currency string (e.g., "1 234,56 Kč").
    var czk: String {
        let number = NSDecimalNumber(decimal: self)
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CZK"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: number) ?? "\(number) Kč"
    }
}

extension Date {
    /// Formats as Czech date string (e.g., "17.02.2026").
    var czechFormatted: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd.MM.yyyy"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: self)
    }
}
