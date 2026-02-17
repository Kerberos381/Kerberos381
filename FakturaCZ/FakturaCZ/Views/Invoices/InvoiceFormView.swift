import SwiftUI
import SwiftData

struct InvoiceFormView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    @Query private var subjects: [Subject]

    @State private var selectedSubject: Subject?
    @State private var invoiceType: InvoiceType = .standard
    @State private var issuedDate = Date()
    @State private var taxableSupplyDate = Date()
    @State private var dueDate = Calendar.current.date(byAdding: .day, value: 14, to: Date())!
    @State private var supplyCode: SupplyCode = .domestic
    @State private var variableSymbol = ""
    @State private var bankAccount = ""
    @State private var note = ""
    @State private var lines: [LineFormItem] = [LineFormItem()]

    var body: some View {
        NavigationStack {
            Form {
                // MARK: - Type & Subject
                Section("Základní údaje") {
                    Picker("Typ", selection: $invoiceType) {
                        ForEach(InvoiceType.allCases) { type in
                            Text(type.label).tag(type)
                        }
                    }

                    Picker("Odběratel", selection: $selectedSubject) {
                        Text("Vyberte...").tag(nil as Subject?)
                        ForEach(subjects, id: \.registrationNo) { subject in
                            Text(subject.name).tag(subject as Subject?)
                        }
                    }
                }

                // MARK: - Dates
                Section("Termíny") {
                    DatePicker("Datum vystavení", selection: $issuedDate, displayedComponents: .date)
                    DatePicker("DUZP", selection: $taxableSupplyDate, displayedComponents: .date)
                    DatePicker("Splatnost", selection: $dueDate, displayedComponents: .date)
                }

                // MARK: - Payment
                Section("Platba") {
                    Picker("Typ plnění", selection: $supplyCode) {
                        ForEach(SupplyCode.allCases) { code in
                            Text(code.label).tag(code)
                        }
                    }
                    TextField("Variabilní symbol", text: $variableSymbol)
                        .keyboardType(.numberPad)
                    TextField("Číslo účtu", text: $bankAccount)
                }

                // MARK: - Line Items
                Section("Položky") {
                    ForEach($lines) { $line in
                        VStack(alignment: .leading, spacing: 8) {
                            TextField("Popis", text: $line.description)
                            HStack {
                                TextField("Množství", value: $line.quantity, format: .number)
                                    .keyboardType(.decimalPad)
                                    .frame(width: 80)
                                TextField("Jednotka", text: $line.unit)
                                    .frame(width: 50)
                                TextField("Cena/ks", value: $line.unitPrice, format: .number)
                                    .keyboardType(.decimalPad)
                            }
                            Picker("DPH", selection: $line.vatRate) {
                                ForEach(VATRate.allCases) { rate in
                                    Text(rate.label).tag(rate)
                                }
                            }
                            .pickerStyle(.segmented)

                            HStack {
                                Text("Celkem:")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(formatCurrency(line.total))
                                    .font(.caption.bold())
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .onDelete { lines.remove(atOffsets: $0) }

                    Button {
                        lines.append(LineFormItem())
                    } label: {
                        Label("Přidat položku", systemImage: "plus.circle")
                    }
                }

                // MARK: - Note
                Section("Poznámka") {
                    TextField("Poznámka na fakturu", text: $note, axis: .vertical)
                        .lineLimit(3...6)
                }

                // MARK: - Total
                Section {
                    HStack {
                        Text("Celkem k úhradě")
                            .font(.headline)
                        Spacer()
                        Text(formatCurrency(grandTotal))
                            .font(.title2.bold())
                    }
                }
            }
            .navigationTitle("Nová faktura")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Zrušit") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Vytvořit") {
                        createInvoice()
                    }
                    .disabled(lines.isEmpty)
                }
            }
        }
    }

    private var grandTotal: Decimal {
        let subtotal = lines.reduce(Decimal.zero) { $0 + $1.total }
        return CzechRounding.round(subtotal)
    }

    private func createInvoice() {
        do {
            let number = try InvoiceNumberGenerator.next(context: modelContext)
            let invoice = Invoice(
                invoiceNumber: number,
                type: invoiceType,
                issuedDate: issuedDate,
                taxableSupplyDate: taxableSupplyDate,
                dueDate: dueDate,
                supplyCode: supplyCode,
                variableSymbol: variableSymbol.isEmpty ? nil : variableSymbol,
                note: note.isEmpty ? nil : note
            )
            invoice.subject = selectedSubject
            invoice.bankAccount = bankAccount.isEmpty ? nil : bankAccount

            modelContext.insert(invoice)

            for (index, lineItem) in lines.enumerated() {
                let line = InvoiceLine(
                    itemDescription: lineItem.description,
                    quantity: lineItem.quantity,
                    unitPrice: lineItem.unitPrice,
                    vatRate: lineItem.vatRate,
                    unit: lineItem.unit,
                    sortOrder: index
                )
                line.invoice = invoice
                modelContext.insert(line)
            }

            try modelContext.save()
            dismiss()
        } catch {
            // In production, surface this error to the UI.
            print("Failed to create invoice: \(error)")
        }
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

// MARK: - Line Form Item

struct LineFormItem: Identifiable {
    let id = UUID()
    var description: String = ""
    var quantity: Decimal = 1
    var unitPrice: Decimal = 0
    var vatRate: VATRate = .standard
    var unit: String = "ks"

    var lineTotal: Decimal { quantity * unitPrice }
    var vatAmount: Decimal { lineTotal * vatRate.multiplier }
    var total: Decimal { lineTotal + vatAmount }
}
