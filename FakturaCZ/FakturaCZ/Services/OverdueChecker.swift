import Foundation
import SwiftData

/// Daily check that transitions invoices to the overdue state.
/// In a production iOS app, this runs on app launch and via BGTaskScheduler.
enum OverdueChecker {

    /// Checks all non-paid invoices and marks overdue ones.
    @MainActor
    static func check(context: ModelContext) throws -> Int {
        let now = Date()
        let openState = InvoiceState.open.rawValue
        let sentState = InvoiceState.sent.rawValue

        let predicate = #Predicate<Invoice> { invoice in
            (invoice.stateRaw == openState || invoice.stateRaw == sentState)
        }

        let descriptor = FetchDescriptor<Invoice>(predicate: predicate)
        let invoices = try context.fetch(descriptor)

        var overdueCount = 0
        for invoice in invoices {
            if now > invoice.dueDate {
                invoice.transition(to: .overdue)
                overdueCount += 1
            }
        }

        if overdueCount > 0 {
            try context.save()
        }

        return overdueCount
    }
}
