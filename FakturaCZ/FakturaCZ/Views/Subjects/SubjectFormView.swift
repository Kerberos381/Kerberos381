import SwiftUI

struct SubjectFormView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    @State private var registrationNo = ""
    @State private var name = ""
    @State private var street = ""
    @State private var city = ""
    @State private var zip = ""
    @State private var vatNo = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var bankAccount = ""

    @State private var isLoadingARES = false
    @State private var aresError: String?
    @State private var aresLoaded = false

    var body: some View {
        NavigationStack {
            Form {
                // MARK: - Registration Number + ARES Lookup
                Section {
                    HStack {
                        TextField("IČO (8 číslic)", text: $registrationNo)
                            .keyboardType(.numberPad)

                        Button {
                            Task { await lookupARES() }
                        } label: {
                            if isLoadingARES {
                                ProgressView()
                            } else {
                                Label("ARES", systemImage: "magnifyingglass")
                            }
                        }
                        .buttonStyle(.bordered)
                        .disabled(registrationNo.count != 8 || isLoadingARES)
                    }

                    if let error = aresError {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }

                    if aresLoaded {
                        Text("Data načtena z registru ARES")
                            .font(.caption)
                            .foregroundStyle(.green)
                    }
                } header: {
                    Text("Identifikace")
                } footer: {
                    Text("Zadejte IČO a stiskněte ARES pro automatické vyplnění údajů z registru.")
                }

                // MARK: - Company Details
                Section("Údaje o společnosti") {
                    TextField("Název společnosti", text: $name)
                    TextField("Ulice", text: $street)
                    TextField("Město", text: $city)
                    TextField("PSČ", text: $zip)
                        .keyboardType(.numberPad)
                    TextField("DIČ", text: $vatNo)
                }

                // MARK: - Contact
                Section("Kontakt") {
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .textContentType(.emailAddress)
                    TextField("Telefon", text: $phone)
                        .keyboardType(.phonePad)
                        .textContentType(.telephoneNumber)
                    TextField("Číslo účtu", text: $bankAccount)
                }
            }
            .navigationTitle("Nový subjekt")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Zrušit") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Uložit") {
                        saveSubject()
                    }
                    .disabled(registrationNo.isEmpty || name.isEmpty)
                }
            }
        }
    }

    private func lookupARES() async {
        isLoadingARES = true
        aresError = nil
        aresLoaded = false

        do {
            let data = try await ARESService.shared.fetchSubject(registrationNo: registrationNo)
            name = data.name
            street = data.street
            city = data.city
            zip = data.zip
            vatNo = data.vatNo ?? ""
            aresLoaded = true
        } catch {
            aresError = error.localizedDescription
        }

        isLoadingARES = false
    }

    private func saveSubject() {
        let subject = Subject(
            registrationNo: registrationNo,
            name: name,
            street: street,
            city: city,
            zip: zip,
            vatNo: vatNo.isEmpty ? nil : vatNo,
            email: email.isEmpty ? nil : email,
            phone: phone.isEmpty ? nil : phone,
            bankAccount: bankAccount.isEmpty ? nil : bankAccount
        )

        if aresLoaded {
            subject.lastARESSync = Date()
        }

        modelContext.insert(subject)
        dismiss()
    }
}

#Preview {
    SubjectFormView()
}
