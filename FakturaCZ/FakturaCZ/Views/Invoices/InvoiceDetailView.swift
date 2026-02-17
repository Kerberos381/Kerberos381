import SwiftUI

struct InvoiceDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var invoice: Invoice

    @State private var showingPDFShare = false
    @State private var pdfData: Data?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // MARK: - Header
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(invoice.type.label.uppercased())
                            .font(.caption.bold())
                            .foregroundStyle(.secondary)
                        Text(invoice.invoiceNumber)
                            .font(.title.bold())
                    }
                    Spacer()
                    StateBadge(state: invoice.state)
                }

                if invoice.isLocked {
                    HStack {
                        Image(systemName: "lock.fill")
                        Text("Faktura je uzamčena pro účetní export")
                    }
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .padding(8)
                    .background(Color.orange.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
                }

                // MARK: - Dates
                GroupBox("Termíny") {
                    LabeledRow(label: "Datum vystavení", value: formatDate(invoice.issuedDate))
                    LabeledRow(label: "DUZP", value: formatDate(invoice.taxableSupplyDate))
                    LabeledRow(label: "Splatnost", value: formatDate(invoice.dueDate))
                }

                // MARK: - Subject
                if let subject = invoice.subject {
                    GroupBox("Odběratel") {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(subject.name).font(.subheadline.bold())
                            Text(subject.street).font(.caption)
                            Text("\(subject.zip) \(subject.city)").font(.caption)
                            Text("IČO: \(subject.registrationNo)").font(.caption)
                            if let vatNo = subject.vatNo {
                                Text("DIČ: \(vatNo)").font(.caption)
                            }
                        }
                    }
                }

                // MARK: - Line Items
                GroupBox("Položky") {
                    VStack(spacing: 0) {
                        // Header
                        HStack {
                            Text("Popis").font(.caption.bold()).frame(maxWidth: .infinity, alignment: .leading)
                            Text("Množství").font(.caption.bold()).frame(width: 60, alignment: .trailing)
                            Text("Cena").font(.caption.bold()).frame(width: 80, alignment: .trailing)
                            Text("DPH").font(.caption.bold()).frame(width: 40, alignment: .trailing)
                        }
                        .padding(.bottom, 4)

                        Divider()

                        ForEach(invoice.lines.sorted { $0.sortOrder < $1.sortOrder },
                                id: \.itemDescription) { line in
                            HStack {
                                Text(line.itemDescription)
                                    .font(.caption)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .lineLimit(2)
                                Text("\(formatNumber(line.quantity)) \(line.unit)")
                                    .font(.caption)
                                    .frame(width: 60, alignment: .trailing)
                                Text(formatCurrency(line.lineTotalWithVAT))
                                    .font(.caption)
                                    .frame(width: 80, alignment: .trailing)
                                Text(line.vatRate.label)
                                    .font(.caption2)
                                    .frame(width: 40, alignment: .trailing)
                            }
                            .padding(.vertical, 4)
                            Divider()
                        }
                    }
                }

                // MARK: - VAT Breakdown
                let breakdown = VATCalculator.breakdown(for: invoice.lines)
                if !breakdown.isEmpty {
                    GroupBox("Rekapitulace DPH") {
                        ForEach(breakdown.sorted(by: { $0.key.rawValue > $1.key.rawValue }),
                                id: \.key) { rate, entry in
                            HStack {
                                Text("Sazba \(rate.label)")
                                    .font(.caption)
                                Spacer()
                                VStack(alignment: .trailing) {
                                    Text("Základ: \(formatCurrency(entry.base))")
                                    Text("DPH: \(formatCurrency(entry.vat))")
                                }
                                .font(.caption)
                            }
                        }
                    }
                }

                // MARK: - Totals
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Základ celkem")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(formatCurrency(invoice.subtotal))
                            .font(.subheadline)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("Celkem k úhradě")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(formatCurrency(invoice.total))
                            .font(.title2.bold())
                    }
                }
                .padding()
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))

                // MARK: - Payment Info
                if invoice.variableSymbol != nil || invoice.bankAccount != nil {
                    GroupBox("Platební údaje") {
                        if let vs = invoice.variableSymbol {
                            LabeledRow(label: "Variabilní symbol", value: vs)
                        }
                        if let account = invoice.bankAccount {
                            LabeledRow(label: "Číslo účtu", value: account)
                        }
                    }
                }

                // MARK: - Notes
                if let note = invoice.note, !note.isEmpty {
                    GroupBox("Poznámka") {
                        Text(note)
                            .font(.caption)
                    }
                }

                // MARK: - Actions
                if invoice.isEditable {
                    HStack(spacing: 12) {
                        if invoice.canTransition(to: .sent) {
                            Button {
                                invoice.transition(to: .sent)
                            } label: {
                                Label("Odeslat", systemImage: "paperplane")
                            }
                            .buttonStyle(.borderedProminent)
                        }

                        if invoice.canTransition(to: .paid) {
                            Button {
                                invoice.transition(to: .paid)
                            } label: {
                                Label("Zaplaceno", systemImage: "checkmark.circle")
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
            }
            .padding()
        }
        .navigationTitle(invoice.invoiceNumber)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    pdfData = PDFRenderer.render(invoice: invoice)
                    showingPDFShare = true
                } label: {
                    Image(systemName: "square.and.arrow.up")
                }
            }
        }
        .sheet(isPresented: $showingPDFShare) {
            if let data = pdfData {
                ShareSheet(items: [data])
            }
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "dd.MM.yyyy"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: date)
    }

    private func formatCurrency(_ value: Decimal) -> String {
        let number = NSDecimalNumber(decimal: value)
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CZK"
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: number) ?? "\(number) Kč"
    }

    private func formatNumber(_ value: Decimal) -> String {
        NSDecimalNumber(decimal: value).stringValue
    }
}

// MARK: - Labeled Row

struct LabeledRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.caption.bold())
        }
    }
}

// MARK: - Share Sheet

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
