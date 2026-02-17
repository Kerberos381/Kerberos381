import SwiftUI
import SwiftData

struct TaxReportView: View {
    @Environment(\.modelContext) private var modelContext

    @State private var selectedYear = Calendar.current.component(.year, from: Date())
    @State private var selectedMonth = Calendar.current.component(.month, from: Date())
    @State private var selectedPeriod: TaxPeriod = .monthly
    @State private var taxpayerVATNo = ""

    @State private var dphXML: String?
    @State private var khXML: String?
    @State private var isGenerating = false
    @State private var invoiceCount = 0
    @State private var showingExportSheet = false
    @State private var exportContent = ""
    @State private var isPerformingSharpExport = false
    @State private var sharpExportMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                // MARK: - Period Selection
                Section("Období") {
                    Picker("Typ období", selection: $selectedPeriod) {
                        ForEach(TaxPeriod.allCases) { period in
                            Text(period.label).tag(period)
                        }
                    }

                    Picker("Rok", selection: $selectedYear) {
                        ForEach((2020...2030), id: \.self) { year in
                            Text(String(year)).tag(year)
                        }
                    }

                    if selectedPeriod == .monthly {
                        Picker("Měsíc", selection: $selectedMonth) {
                            ForEach(1...12, id: \.self) { month in
                                Text(czechMonth(month)).tag(month)
                            }
                        }
                    } else {
                        Picker("Čtvrtletí", selection: $selectedMonth) {
                            Text("Q1 (leden–březen)").tag(1)
                            Text("Q2 (duben–červen)").tag(4)
                            Text("Q3 (červenec–září)").tag(7)
                            Text("Q4 (říjen–prosinec)").tag(10)
                        }
                    }

                    TextField("DIČ poplatníka", text: $taxpayerVATNo)
                }

                // MARK: - Generate
                Section {
                    Button {
                        generateReports()
                    } label: {
                        HStack {
                            Label("Generovat přiznání", systemImage: "doc.text.magnifyingglass")
                            if isGenerating {
                                Spacer()
                                ProgressView()
                            }
                        }
                    }
                    .disabled(taxpayerVATNo.isEmpty || isGenerating)

                    if invoiceCount > 0 {
                        Text("Nalezeno \(invoiceCount) faktur pro dané období")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                // MARK: - DPH Output
                if dphXML != nil {
                    Section("Přiznání k DPH (DPHDP3)") {
                        Button {
                            exportContent = dphXML!
                            showingExportSheet = true
                        } label: {
                            Label("Exportovat DPH XML", systemImage: "square.and.arrow.up")
                        }
                    }
                }

                // MARK: - KH Output
                if khXML != nil {
                    Section("Kontrolní hlášení (DPHKH1)") {
                        Button {
                            exportContent = khXML!
                            showingExportSheet = true
                        } label: {
                            Label("Exportovat KH XML", systemImage: "square.and.arrow.up")
                        }
                    }
                }

                // MARK: - Accounting Export
                Section("Účetní export") {
                    Button {
                        performSharpExport()
                    } label: {
                        HStack {
                            Label("Ostrý export (uzamkne faktury)", systemImage: "lock.doc")
                            if isPerformingSharpExport {
                                Spacer()
                                ProgressView()
                            }
                        }
                    }
                    .disabled(invoiceCount == 0 || isPerformingSharpExport)

                    if let message = sharpExportMessage {
                        Text(message)
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }

                    Button {
                        exportPohoda()
                    } label: {
                        Label("Export pro Pohoda", systemImage: "arrow.down.doc")
                    }
                    .disabled(invoiceCount == 0)
                }
            }
            .navigationTitle("Daňové přehledy")
            .sheet(isPresented: $showingExportSheet) {
                ShareSheet(items: [exportContent])
            }
        }
    }

    // MARK: - Actions

    private func generateReports() {
        isGenerating = true
        do {
            let invoices = try TaxReportGenerator.fetchTaxableInvoices(
                year: selectedYear,
                month: selectedMonth,
                period: selectedPeriod,
                context: modelContext
            )
            invoiceCount = invoices.count

            dphXML = TaxReportGenerator.generateDPHXML(
                invoices: invoices,
                taxpayerVATNo: taxpayerVATNo,
                year: selectedYear,
                month: selectedMonth,
                period: selectedPeriod
            )

            khXML = TaxReportGenerator.generateKHXML(
                invoices: invoices,
                taxpayerVATNo: taxpayerVATNo,
                year: selectedYear,
                month: selectedMonth
            )
        } catch {
            print("Tax report generation failed: \(error)")
        }
        isGenerating = false
    }

    private func performSharpExport() {
        isPerformingSharpExport = true
        sharpExportMessage = nil
        do {
            let invoices = try TaxReportGenerator.fetchTaxableInvoices(
                year: selectedYear,
                month: selectedMonth,
                period: selectedPeriod,
                context: modelContext
            )

            let record = try AccountingExporter.performSharpExport(
                invoices: invoices,
                exportType: "ISDOC",
                year: selectedYear,
                month: selectedMonth,
                context: modelContext
            )

            sharpExportMessage = "Uzamčeno \(record.invoiceIDs.count) faktur. Export vytvořen."
        } catch {
            sharpExportMessage = "Chyba: \(error.localizedDescription)"
        }
        isPerformingSharpExport = false
    }

    private func exportPohoda() {
        do {
            let invoices = try TaxReportGenerator.fetchTaxableInvoices(
                year: selectedYear,
                month: selectedMonth,
                period: selectedPeriod,
                context: modelContext
            )
            let xml = AccountingExporter.generatePohodaXML(invoices: invoices)
            exportContent = xml
            showingExportSheet = true
        } catch {
            print("Pohoda export failed: \(error)")
        }
    }

    private func czechMonth(_ month: Int) -> String {
        let months = [
            "Leden", "Únor", "Březen", "Duben", "Květen", "Červen",
            "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"
        ]
        return months[month - 1]
    }
}

#Preview {
    TaxReportView()
}
