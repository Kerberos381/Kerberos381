import SwiftUI
import SwiftData

struct SubjectListView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \Subject.name) private var subjects: [Subject]

    @State private var searchText = ""
    @State private var showingNewSubject = false

    var filteredSubjects: [Subject] {
        if searchText.isEmpty { return subjects }
        return subjects.filter {
            $0.name.localizedCaseInsensitiveContains(searchText) ||
            $0.registrationNo.contains(searchText)
        }
    }

    var body: some View {
        NavigationStack {
            List {
                ForEach(filteredSubjects, id: \.registrationNo) { subject in
                    NavigationLink(value: subject) {
                        SubjectRow(subject: subject)
                    }
                }
                .onDelete(perform: deleteSubjects)
            }
            .searchable(text: $searchText, prompt: "Hledat subjekt (název, IČO)...")
            .navigationTitle("Subjekty")
            .navigationDestination(for: Subject.self) { subject in
                SubjectDetailView(subject: subject)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingNewSubject = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingNewSubject) {
                SubjectFormView()
            }
            .overlay {
                if subjects.isEmpty {
                    ContentUnavailableView(
                        "Žádné subjekty",
                        systemImage: "person.2.slash",
                        description: Text("Přidejte svého prvního klienta pomocí tlačítka +")
                    )
                }
            }
        }
    }

    private func deleteSubjects(at offsets: IndexSet) {
        for index in offsets {
            let subject = filteredSubjects[index]
            guard subject.invoices.isEmpty else { continue }
            modelContext.delete(subject)
        }
    }
}

// MARK: - Subject Row

struct SubjectRow: View {
    let subject: Subject

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(subject.name)
                    .font(.subheadline.bold())
                    .lineLimit(1)
                Text("IČO: \(subject.registrationNo)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            if subject.isVATPayer {
                Text("Plátce DPH")
                    .font(.caption2.bold())
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.green.opacity(0.15), in: Capsule())
                    .foregroundStyle(.green)
            }
        }
    }
}

#Preview {
    SubjectListView()
}
