import Foundation
import SwiftData

/// A business subject (client/supplier) identified by Czech registration number (IČO).
@Model
final class Subject {
    // MARK: - Identifiers

    /// Czech registration number (IČO) — the primary business identifier.
    @Attribute(.unique)
    var registrationNo: String

    // MARK: - Business Details (enriched from ARES)

    var name: String
    var street: String
    var city: String
    var zip: String

    /// Czech VAT number (DIČ), nil if not a VAT payer.
    var vatNo: String?

    /// Derived flag: true if vatNo is non-nil and non-empty.
    var isVATPayer: Bool {
        guard let vat = vatNo else { return false }
        return !vat.isEmpty
    }

    // MARK: - Contact (user-provided)

    var email: String?
    var phone: String?
    var bankAccount: String?
    var iban: String?

    // MARK: - Metadata

    var createdAt: Date
    var updatedAt: Date

    /// Date of last successful ARES sync.
    var lastARESSync: Date?

    // MARK: - Relationships

    @Relationship(deleteRule: .deny, inverse: \Invoice.subject)
    var invoices: [Invoice] = []

    // MARK: - Init

    init(
        registrationNo: String,
        name: String = "",
        street: String = "",
        city: String = "",
        zip: String = "",
        vatNo: String? = nil,
        email: String? = nil,
        phone: String? = nil,
        bankAccount: String? = nil,
        iban: String? = nil
    ) {
        self.registrationNo = registrationNo
        self.name = name
        self.street = street
        self.city = city
        self.zip = zip
        self.vatNo = vatNo
        self.email = email
        self.phone = phone
        self.bankAccount = bankAccount
        self.iban = iban
        self.createdAt = Date()
        self.updatedAt = Date()
    }

    // MARK: - ARES Update

    /// Apply data retrieved from the ARES registry.
    func applyARESData(_ data: ARESData) {
        self.name = data.name
        self.street = data.street
        self.city = data.city
        self.zip = data.zip
        self.vatNo = data.vatNo
        self.lastARESSync = Date()
        self.updatedAt = Date()
    }

    // MARK: - Display

    var formattedAddress: String {
        [street, "\(zip) \(city)"].filter { !$0.isEmpty }.joined(separator: "\n")
    }
}
