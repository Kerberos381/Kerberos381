import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Přehled", systemImage: "chart.bar")
                }

            InvoiceListView()
                .tabItem {
                    Label("Faktury", systemImage: "doc.text")
                }

            SubjectListView()
                .tabItem {
                    Label("Subjekty", systemImage: "person.2")
                }

            TaxReportView()
                .tabItem {
                    Label("Daně", systemImage: "building.columns")
                }
        }
    }
}

#Preview {
    ContentView()
}
