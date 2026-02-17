import Foundation
import SwiftData

/// Generates sequential invoice numbers in the format "YYYY-NNNN".
enum InvoiceNumberGenerator {

    /// Generates the next invoice number for the given year.
    @MainActor
    static func next(
        year: Int? = nil,
        context: ModelContext
    ) throws -> String {
        let targetYear = year ?? Calendar.current.component(.year, from: Date())
        let prefix = String(targetYear)

        // Find the highest existing invoice number for this year.
        let predicate = #Predicate<Invoice> { invoice in
            invoice.invoiceNumber.starts(with: prefix)
        }
        var descriptor = FetchDescriptor<Invoice>(predicate: predicate)
        descriptor.sortBy = [SortDescriptor(\Invoice.invoiceNumber, order: .reverse)]
        descriptor.fetchLimit = 1

        let existing = try context.fetch(descriptor)

        let nextSeq: Int
        if let last = existing.first?.invoiceNumber,
           let seqPart = last.split(separator: "-").last,
           let seq = Int(seqPart) {
            nextSeq = seq + 1
        } else {
            nextSeq = 1
        }

        return String(format: "%d-%04d", targetYear, nextSeq)
    }
}
