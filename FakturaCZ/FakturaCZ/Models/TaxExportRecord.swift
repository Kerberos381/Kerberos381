import Foundation
import SwiftData

/// Tracks accounting export batches and the immutability lock trigger.
@Model
final class TaxExportRecord {
    // MARK: - Export Info

    var exportType: String  // "DPH", "KH", "ISDOC", "Pohoda"
    var periodYear: Int
    var periodMonth: Int

    /// Whether this is a "sharp" (final) export that triggers invoice locking.
    var isSharp: Bool

    /// IDs of invoices included in this export.
    var invoiceIDs: [String]

    // MARK: - Output

    /// Path or data reference to the generated XML/export file.
    var outputFileName: String?

    // MARK: - Metadata

    var createdAt: Date

    init(
        exportType: String,
        periodYear: Int,
        periodMonth: Int,
        isSharp: Bool,
        invoiceIDs: [String]
    ) {
        self.exportType = exportType
        self.periodYear = periodYear
        self.periodMonth = periodMonth
        self.isSharp = isSharp
        self.invoiceIDs = invoiceIDs
        self.createdAt = Date()
    }
}
