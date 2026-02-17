import SwiftUI

struct SubjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var subject: Subject

    @State private var isRefreshing = false
    @State private var refreshError: String?

    var body: some View {
        List {
            // MARK: - Company Info
            Section("Údaje o společnosti") {
                LabeledRow(label: "Název", value: subject.name)
                LabeledRow(label: "IČO", value: subject.registrationNo)
                if let vatNo = subject.vatNo {
                    LabeledRow(label: "DIČ", value: vatNo)
                }
                LabeledRow(label: "Plátce DPH", value: subject.isVATPayer ? "Ano" : "Ne")
            }

            // MARK: - Address
            Section("Adresa") {
                LabeledRow(label: "Ulice", value: subject.street)
                LabeledRow(label: "Město", value: subject.city)
                LabeledRow(label: "PSČ", value: subject.zip)
            }

            // MARK: - Contact
            Section("Kontakt") {
                if let email = subject.email, !email.isEmpty {
                    LabeledRow(label: "Email", value: email)
                }
                if let phone = subject.phone, !phone.isEmpty {
                    LabeledRow(label: "Telefon", value: phone)
                }
                if let account = subject.bankAccount, !account.isEmpty {
                    LabeledRow(label: "Číslo účtu", value: account)
                }
            }

            // MARK: - ARES Sync
            Section("ARES") {
                if let lastSync = subject.lastARESSync {
                    LabeledRow(label: "Poslední synchronizace", value: formatDate(lastSync))
                }

                Button {
                    Task { await refreshFromARES() }
                } label: {
                    HStack {
                        Label("Obnovit z ARES", systemImage: "arrow.clockwise")
                        if isRefreshing {
                            Spacer()
                            ProgressView()
                        }
                    }
                }
                .disabled(isRefreshing)

                if let error = refreshError {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }
            }

            // MARK: - Invoices
            if !subject.invoices.isEmpty {
                Section("Faktury (\(subject.invoices.count))") {
                    ForEach(subject.invoices.sorted { $0.createdAt > $1.createdAt },
                            id: \.invoiceNumber) { invoice in
                        NavigationLink(value: invoice) {
                            InvoiceRow(invoice: invoice)
                        }
                    }
                }
            }
        }
        .navigationTitle(subject.name)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func refreshFromARES() async {
        isRefreshing = true
        refreshError = nil

        do {
            let data = try await ARESService.shared.fetchSubject(
                registrationNo: subject.registrationNo
            )
            subject.applyARESData(data)
            try modelContext.save()
        } catch {
            refreshError = error.localizedDescription
        }

        isRefreshing = false
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: date)
    }
}
