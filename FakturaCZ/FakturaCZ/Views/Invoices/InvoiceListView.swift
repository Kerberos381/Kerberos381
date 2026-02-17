import SwiftUI
import SwiftData

struct InvoiceListView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Invoice.createdAt, order: .reverse) private var invoices: [Invoice]

    @State private var searchText = ""
    @State private var filterState: InvoiceState?
    @State private var showingNewInvoice = false

    var filteredInvoices: [Invoice] {
        var result = invoices
        if let filter = filterState {
            result = result.filter { $0.state == filter }
        }
        if !searchText.isEmpty {
            result = result.filter {
                $0.invoiceNumber.localizedCaseInsensitiveContains(searchText) ||
                ($0.subject?.name ?? "").localizedCaseInsensitiveContains(searchText)
            }
        }
        return result
    }

    var body: some View {
        NavigationStack {
            List {
                // MARK: - State Filter
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        FilterChip(title: "Vše", isSelected: filterState == nil) {
                            filterState = nil
                        }
                        ForEach(InvoiceState.allCases) { state in
                            FilterChip(title: state.label, isSelected: filterState == state) {
                                filterState = state
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
                .listRowSeparator(.hidden)

                // MARK: - Invoice List
                ForEach(filteredInvoices, id: \.invoiceNumber) { invoice in
                    NavigationLink(value: invoice) {
                        InvoiceRow(invoice: invoice)
                    }
                }
                .onDelete(perform: deleteInvoices)
            }
            .searchable(text: $searchText, prompt: "Hledat fakturu...")
            .navigationTitle("Faktury")
            .navigationDestination(for: Invoice.self) { invoice in
                InvoiceDetailView(invoice: invoice)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingNewInvoice = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingNewInvoice) {
                InvoiceFormView()
            }
        }
    }

    private func deleteInvoices(at offsets: IndexSet) {
        for index in offsets {
            let invoice = filteredInvoices[index]
            guard !invoice.isLocked else { continue }
            modelContext.delete(invoice)
        }
    }
}

// MARK: - Invoice Row

struct InvoiceRow: View {
    let invoice: Invoice

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(invoice.invoiceNumber)
                        .font(.subheadline.bold())
                    StateBadge(state: invoice.state)
                }
                Text(invoice.subject?.name ?? "Bez subjektu")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(formatCurrency(invoice.total))
                    .font(.subheadline.bold())
                Text(formatDate(invoice.dueDate))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    private func formatCurrency(_ value: Decimal) -> String {
        let number = NSDecimalNumber(decimal: value)
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CZK"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: number) ?? "\(number) Kč"
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd.MM.yyyy"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: date)
    }
}

// MARK: - State Badge

struct StateBadge: View {
    let state: InvoiceState

    var color: Color {
        switch state {
        case .open: return .blue
        case .sent: return .orange
        case .overdue: return .red
        case .paid: return .green
        }
    }

    var body: some View {
        Text(state.label)
            .font(.caption2.bold())
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.15), in: Capsule())
            .foregroundStyle(color)
    }
}

// MARK: - Filter Chip

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.caption.bold())
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(isSelected ? Color.accentColor : Color.gray.opacity(0.15),
                            in: Capsule())
                .foregroundStyle(isSelected ? .white : .primary)
        }
    }
}

#Preview {
    InvoiceListView()
}
