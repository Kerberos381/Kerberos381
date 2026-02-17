import Foundation
import UIKit
import PDFKit

/// Renders an invoice to a PDF document using UIKit drawing.
enum PDFRenderer {

    static func render(invoice: Invoice) -> Data {
        let pageRect = CGRect(x: 0, y: 0, width: 595.2, height: 841.8)  // A4
        let margin: CGFloat = 50
        let contentWidth = pageRect.width - 2 * margin

        let renderer = UIGraphicsPDFRenderer(bounds: pageRect)

        return renderer.pdfData { context in
            context.beginPage()
            var y: CGFloat = margin

            // MARK: - Header
            let titleAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 22, weight: .bold),
                .foregroundColor: UIColor.black
            ]
            let title = invoice.type.label.uppercased() + " č. " + invoice.invoiceNumber
            title.draw(at: CGPoint(x: margin, y: y), withAttributes: titleAttrs)
            y += 35

            // MARK: - State badge
            let stateAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 11, weight: .medium),
                .foregroundColor: UIColor.darkGray
            ]
            let stateText = "Stav: \(invoice.state.label)"
            stateText.draw(at: CGPoint(x: margin, y: y), withAttributes: stateAttrs)
            y += 30

            // MARK: - Separator
            drawLine(in: context.cgContext, from: CGPoint(x: margin, y: y),
                     to: CGPoint(x: pageRect.width - margin, y: y))
            y += 15

            // MARK: - Dates
            let bodyAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 10),
                .foregroundColor: UIColor.black
            ]
            let labelAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 10, weight: .semibold),
                .foregroundColor: UIColor.black
            ]

            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "dd.MM.yyyy"
            dateFormatter.locale = Locale(identifier: "cs_CZ")

            let dates: [(String, Date)] = [
                ("Datum vystavení:", invoice.issuedDate),
                ("Datum zdanitelného plnění:", invoice.taxableSupplyDate),
                ("Datum splatnosti:", invoice.dueDate)
            ]

            for (label, date) in dates {
                label.draw(at: CGPoint(x: margin, y: y), withAttributes: labelAttrs)
                let dateStr = dateFormatter.string(from: date)
                dateStr.draw(at: CGPoint(x: margin + 200, y: y), withAttributes: bodyAttrs)
                y += 16
            }
            y += 10

            // MARK: - Subject (buyer)
            if let subject = invoice.subject {
                "Odběratel:".draw(at: CGPoint(x: margin, y: y), withAttributes: labelAttrs)
                y += 18
                subject.name.draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                y += 14
                subject.street.draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                y += 14
                "\(subject.zip) \(subject.city)".draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                y += 14
                "IČO: \(subject.registrationNo)".draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                y += 14
                if let vatNo = subject.vatNo {
                    "DIČ: \(vatNo)".draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                    y += 14
                }
                y += 10
            }

            // MARK: - Separator
            drawLine(in: context.cgContext, from: CGPoint(x: margin, y: y),
                     to: CGPoint(x: pageRect.width - margin, y: y))
            y += 15

            // MARK: - Line Items Table Header
            let headerAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 9, weight: .bold),
                .foregroundColor: UIColor.black
            ]
            let columns: [(String, CGFloat)] = [
                ("Popis", margin),
                ("Množství", margin + 230),
                ("Jedn.", margin + 300),
                ("Cena/ks", margin + 345),
                ("DPH", margin + 410),
                ("Celkem", margin + 450)
            ]
            for (header, x) in columns {
                header.draw(at: CGPoint(x: x, y: y), withAttributes: headerAttrs)
            }
            y += 16

            drawLine(in: context.cgContext, from: CGPoint(x: margin, y: y),
                     to: CGPoint(x: pageRect.width - margin, y: y), lineWidth: 0.5)
            y += 5

            // MARK: - Line Items
            let lineAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 9),
                .foregroundColor: UIColor.black
            ]

            let sortedLines = invoice.lines.sorted { $0.sortOrder < $1.sortOrder }
            for line in sortedLines {
                line.itemDescription.draw(at: CGPoint(x: margin, y: y), withAttributes: lineAttrs)
                formatNumber(line.quantity).draw(at: CGPoint(x: margin + 230, y: y), withAttributes: lineAttrs)
                line.unit.draw(at: CGPoint(x: margin + 300, y: y), withAttributes: lineAttrs)
                formatCurrency(line.unitPrice).draw(at: CGPoint(x: margin + 345, y: y), withAttributes: lineAttrs)
                line.vatRate.label.draw(at: CGPoint(x: margin + 410, y: y), withAttributes: lineAttrs)
                formatCurrency(line.lineTotalWithVAT).draw(at: CGPoint(x: margin + 450, y: y), withAttributes: lineAttrs)
                y += 15
            }

            y += 10
            drawLine(in: context.cgContext, from: CGPoint(x: margin, y: y),
                     to: CGPoint(x: pageRect.width - margin, y: y))
            y += 15

            // MARK: - VAT Breakdown
            let breakdown = VATCalculator.breakdown(for: sortedLines)
            for (rate, entry) in breakdown.sorted(by: { $0.key.rawValue > $1.key.rawValue }) {
                let breakdownText = "Základ \(rate.label): \(formatCurrency(entry.base))   DPH: \(formatCurrency(entry.vat))"
                breakdownText.draw(at: CGPoint(x: margin + 250, y: y), withAttributes: lineAttrs)
                y += 14
            }

            y += 10

            // MARK: - Totals
            let totalAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 14, weight: .bold),
                .foregroundColor: UIColor.black
            ]
            "Celkem k úhradě:".draw(at: CGPoint(x: margin + 250, y: y), withAttributes: labelAttrs)
            formatCurrency(invoice.total).draw(at: CGPoint(x: margin + 400, y: y), withAttributes: totalAttrs)
            y += 25

            // MARK: - Payment info
            if let vs = invoice.variableSymbol {
                "Variabilní symbol: \(vs)".draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                y += 14
            }
            if let account = invoice.bankAccount {
                "Číslo účtu: \(account)".draw(at: CGPoint(x: margin, y: y), withAttributes: bodyAttrs)
                y += 14
            }

            // MARK: - Notes
            if let note = invoice.note, !note.isEmpty {
                y += 15
                "Poznámka:".draw(at: CGPoint(x: margin, y: y), withAttributes: labelAttrs)
                y += 16
                let noteRect = CGRect(x: margin, y: y, width: contentWidth, height: 60)
                note.draw(in: noteRect, withAttributes: bodyAttrs)
            }
        }
    }

    // MARK: - Drawing Helpers

    private static func drawLine(
        in cgContext: CGContext,
        from: CGPoint,
        to: CGPoint,
        lineWidth: CGFloat = 1.0
    ) {
        cgContext.setStrokeColor(UIColor.gray.cgColor)
        cgContext.setLineWidth(lineWidth)
        cgContext.move(to: from)
        cgContext.addLine(to: to)
        cgContext.strokePath()
    }

    private static func formatCurrency(_ value: Decimal) -> String {
        let number = NSDecimalNumber(decimal: CzechRounding.round(value))
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.minimumFractionDigits = 2
        formatter.maximumFractionDigits = 2
        formatter.groupingSeparator = " "
        formatter.decimalSeparator = ","
        formatter.locale = Locale(identifier: "cs_CZ")
        return (formatter.string(from: number) ?? number.stringValue) + " Kč"
    }

    private static func formatNumber(_ value: Decimal) -> String {
        let number = NSDecimalNumber(decimal: value)
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        formatter.locale = Locale(identifier: "cs_CZ")
        return formatter.string(from: number) ?? number.stringValue
    }
}
