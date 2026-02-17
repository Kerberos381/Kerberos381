import Foundation
import SwiftData

/// Cron-equivalent scheduler that checks recurring templates and generates invoices.
actor RecurringScheduler {
    static let shared = RecurringScheduler()

    private init() {}

    /// Checks all active recurring templates and generates invoices for those due today.
    /// Should be called on app launch and periodically via background tasks.
    @MainActor
    func processTemplates(context: ModelContext) async throws -> [Invoice] {
        let predicate = #Predicate<RecurringTemplate> { template in
            template.isActive
        }
        let descriptor = FetchDescriptor<RecurringTemplate>(predicate: predicate)
        let templates = try context.fetch(descriptor)

        var generated: [Invoice] = []

        for template in templates {
            guard template.isDueToday else { continue }

            let invoice = try generateInvoice(from: template, context: context)
            generated.append(invoice)

            template.advance()
        }

        if !generated.isEmpty {
            try context.save()
        }

        return generated
    }

    /// Creates a new Invoice from a RecurringTemplate.
    @MainActor
    private func generateInvoice(
        from template: RecurringTemplate,
        context: ModelContext
    ) throws -> Invoice {
        let invoiceNumber = try InvoiceNumberGenerator.next(context: context)
        let now = Date()
        let dueDate = Calendar.current.date(
            byAdding: .day,
            value: template.paymentTermDays,
            to: now
        )!

        let invoice = Invoice(
            invoiceNumber: invoiceNumber,
            type: .standard,
            issuedDate: now,
            taxableSupplyDate: now,
            dueDate: dueDate,
            supplyCode: template.supplyCode
        )
        invoice.subject = template.subject
        invoice.note = template.defaultNote

        // Decode line item specs and create InvoiceLine objects.
        if let lineData = template.lineItemsJSON {
            let decoder = JSONDecoder()
            if let specs = try? decoder.decode([LineItemSpec].self, from: lineData) {
                for (index, spec) in specs.enumerated() {
                    let resolvedDescription = template.resolveDescription(for: now)
                        .isEmpty ? spec.description : template.resolveDescription(for: now)

                    let line = InvoiceLine(
                        itemDescription: resolvedDescription,
                        quantity: spec.quantity,
                        unitPrice: spec.unitPrice,
                        vatRate: VATRate(rawValue: spec.vatRate) ?? .standard,
                        unit: spec.unit,
                        sortOrder: index
                    )
                    line.invoice = invoice
                    context.insert(line)
                }
            }
        }

        context.insert(invoice)
        return invoice
    }
}
