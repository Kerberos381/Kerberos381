import SwiftUI
import SwiftData

@main
struct FakturaCZApp: App {
    let modelContainer: ModelContainer

    init() {
        do {
            let schema = Schema([
                Subject.self,
                Invoice.self,
                InvoiceLine.self,
                RecurringTemplate.self,
                TaxExportRecord.self
            ])
            let config = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
            modelContainer = try ModelContainer(for: schema, configurations: [config])
        } catch {
            fatalError("Failed to initialize ModelContainer: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(modelContainer)
    }
}
