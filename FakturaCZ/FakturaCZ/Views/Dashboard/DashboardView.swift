import SwiftUI
import SwiftData

struct DashboardView: View {
    @Environment(\.modelContext) private var modelContext

    @Query(filter: #Predicate<Invoice> { $0.stateRaw == "open" })
    private var openInvoices: [Invoice]

    @Query(filter: #Predicate<Invoice> { $0.stateRaw == "overdue" })
    private var overdueInvoices: [Invoice]

    @Query(filter: #Predicate<Invoice> { $0.stateRaw == "sent" })
    private var sentInvoices: [Invoice]

    @Query private var allInvoices: [Invoice]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // MARK: - Summary Cards
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 16) {
                        SummaryCard(
                            title: "Otevřené",
                            count: openInvoices.count,
                            amount: openInvoices.reduce(Decimal.zero) { $0 + $1.total },
                            color: .blue,
                            icon: "doc.badge.ellipsis"
                        )
                        SummaryCard(
                            title: "Po splatnosti",
                            count: overdueInvoices.count,
                            amount: overdueInvoices.reduce(Decimal.zero) { $0 + $1.total },
                            color: .red,
                            icon: "exclamationmark.triangle"
                        )
                        SummaryCard(
                            title: "Odeslané",
                            count: sentInvoices.count,
                            amount: sentInvoices.reduce(Decimal.zero) { $0 + $1.total },
                            color: .orange,
                            icon: "paperplane"
                        )
                        SummaryCard(
                            title: "Celkem faktur",
                            count: allInvoices.count,
                            amount: allInvoices.reduce(Decimal.zero) { $0 + $1.total },
                            color: .green,
                            icon: "chart.bar"
                        )
                    }
                    .padding(.horizontal)

                    // MARK: - Recent Overdue
                    if !overdueInvoices.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Po splatnosti")
                                .font(.headline)
                                .padding(.horizontal)

                            ForEach(overdueInvoices.prefix(5), id: \.invoiceNumber) { invoice in
                                OverdueRow(invoice: invoice)
                            }
                        }
                    }

                    // MARK: - Recent Invoices
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Poslední faktury")
                            .font(.headline)
                            .padding(.horizontal)

                        let recent = allInvoices
                            .sorted { $0.createdAt > $1.createdAt }
                            .prefix(10)

                        ForEach(Array(recent), id: \.invoiceNumber) { invoice in
                            InvoiceRow(invoice: invoice)
                        }
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Přehled")
            .task {
                // Run overdue check on appear.
                try? OverdueChecker.check(context: modelContext)
            }
        }
    }
}

// MARK: - Summary Card

struct SummaryCard: View {
    let title: String
    let count: Int
    let amount: Decimal
    let color: Color
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Spacer()
                Text("\(count)")
                    .font(.title2.bold())
            }

            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)

            Text(formatCurrency(amount))
                .font(.subheadline.bold())
                .foregroundStyle(color)
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func formatCurrency(_ value: Decimal) -> String {
        let number = NSDecimalNumber(decimal: value)
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CZK"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: number) ?? "\(number) Kč"
    }
}

// MARK: - Overdue Row

struct OverdueRow: View {
    let invoice: Invoice

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(invoice.invoiceNumber)
                    .font(.subheadline.bold())
                Text(invoice.subject?.name ?? "—")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing) {
                Text(formatCurrency(invoice.total))
                    .font(.subheadline.bold())
                    .foregroundStyle(.red)
                Text(daysOverdue)
                    .font(.caption2)
                    .foregroundStyle(.red)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
    }

    private var daysOverdue: String {
        let days = Calendar.current.dateComponents([.day], from: invoice.dueDate, to: Date()).day ?? 0
        return "\(days) dní po splatnosti"
    }

    private func formatCurrency(_ value: Decimal) -> String {
        let number = NSDecimalNumber(decimal: value)
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CZK"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: number) ?? "\(number) Kč"
    }
}

#Preview {
    DashboardView()
}
