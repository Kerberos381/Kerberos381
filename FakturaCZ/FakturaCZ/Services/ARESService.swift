import Foundation

// MARK: - ARES Data Transfer Object

struct ARESData {
    let registrationNo: String
    let name: String
    let street: String
    let city: String
    let zip: String
    let vatNo: String?
}

// MARK: - ARES API Response Models

/// Root response from the ARES REST API (https://ares.gov.cz/ekonomicke-subjekty-v-be/rest)
private struct ARESResponse: Decodable {
    let ico: String?
    let obchodniJmeno: String?
    let sidlo: ARESSidlo?
    let dic: String?
}

private struct ARESSidlo: Decodable {
    let textovaAdresa: String?
    let nazevObce: String?
    let psc: Int?
    let nazevUlice: String?
    let cisloDomovni: Int?
    let cisloOrientacni: Int?
}

// MARK: - ARES Service

enum ARESError: LocalizedError {
    case invalidRegistrationNo
    case networkError(Error)
    case notFound
    case decodingError(Error)
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidRegistrationNo:
            return "Neplatné IČO. IČO musí mít 8 číslic."
        case .networkError(let error):
            return "Chyba sítě: \(error.localizedDescription)"
        case .notFound:
            return "Subjekt nebyl nalezen v registru ARES."
        case .decodingError(let error):
            return "Chyba zpracování odpovědi: \(error.localizedDescription)"
        case .serverError(let code):
            return "Server ARES vrátil chybu: \(code)"
        }
    }
}

/// Service for querying the Czech ARES registry to enrich subject data.
actor ARESService {
    static let shared = ARESService()

    private let session: URLSession
    private let baseURL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 15
        config.timeoutIntervalForResource = 30
        self.session = URLSession(configuration: config)
    }

    /// Fetches subject data from ARES by registration number (IČO).
    /// - Parameter registrationNo: 8-digit Czech IČO.
    /// - Returns: Enriched `ARESData`.
    func fetchSubject(registrationNo: String) async throws -> ARESData {
        let cleaned = registrationNo.trimmingCharacters(in: .whitespaces)

        guard cleaned.count == 8, cleaned.allSatisfy(\.isNumber) else {
            throw ARESError.invalidRegistrationNo
        }

        let url = URL(string: "\(baseURL)/\(cleaned)")!
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw ARESError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ARESError.networkError(URLError(.badServerResponse))
        }

        switch httpResponse.statusCode {
        case 200:
            break
        case 404:
            throw ARESError.notFound
        default:
            throw ARESError.serverError(httpResponse.statusCode)
        }

        let decoded: ARESResponse
        do {
            decoded = try JSONDecoder().decode(ARESResponse.self, from: data)
        } catch {
            throw ARESError.decodingError(error)
        }

        let sidlo = decoded.sidlo
        let street = buildStreet(from: sidlo)

        return ARESData(
            registrationNo: cleaned,
            name: decoded.obchodniJmeno ?? "",
            street: street,
            city: sidlo?.nazevObce ?? "",
            zip: sidlo?.psc.map { String($0) } ?? "",
            vatNo: decoded.dic
        )
    }

    private func buildStreet(from sidlo: ARESSidlo?) -> String {
        guard let sidlo else { return "" }

        // If textovaAdresa is available, prefer it.
        if let full = sidlo.textovaAdresa, !full.isEmpty {
            return full
        }

        // Otherwise, construct from components.
        var parts: [String] = []
        if let street = sidlo.nazevUlice, !street.isEmpty {
            parts.append(street)
        }
        if let domovni = sidlo.cisloDomovni {
            if let orientacni = sidlo.cisloOrientacni {
                parts.append("\(domovni)/\(orientacni)")
            } else {
                parts.append(String(domovni))
            }
        }
        return parts.joined(separator: " ")
    }
}
