# Generátor Platebních QR Kódů (Payment QR Code Generator - Czech Republic)

This project is a client-side web application that generates QR codes for payments within the Czech Republic, adhering to the Short Payment Descriptor (SPD) standard. Users can input payment details, and the tool will generate a scannable QR code and offer a PDF download of the QR code along with the entered information.

## Features

* **Czech Payment Standard (SPD):** Generates QR codes compatible with the Czech banking system.
* **IBAN Calculation:** Automatically calculates the Czech IBAN from the account prefix, number, and bank code.
* **Dynamic Bank Codes:** Loads bank codes from an external `bank_codes.json` file.
* **User-Friendly Form:** Allows input for:
    * Receiver Name
    * Account Prefix
    * Account Number (mandatory)
    * Bank Code (mandatory, selectable)
    * Amount
    * Variable Symbol (VS)
    * Constant Symbol (KS)
    * Specific Symbol (SS)
    * Message for recipient
* **QR Code Display:** Renders the QR code directly on the page.
* **PDF Export:** Allows users to download the QR code and payment details as a PDF document.
* **Input Validation:** Basic validation for mandatory fields and character handling for QR code compatibility.
* **Account Number Parsing:** Supports pasting combined account information (prefix-number/bankcode).
* **Responsive Design:** Adapts to different screen sizes.
* **Client-Side:** All operations are performed in the user's browser; no server-side processing is required for the core functionality.

## Technologies Used

* HTML5
* CSS3
* JavaScript (ES6+)
* [QRCode.js](https://github.com/davidshimjs/qrcodejs) - For QR code generation.
* [pdfmake](http://pdfmake.org/) - For PDF generation.
* Font Awesome - For icons.

## How to Use

1.  Open `index.html` in a web browser.
2.  Fill in the payment details in the form on the right.
    * Fields marked with an asterisk (*) are mandatory.
3.  Click the "Generovat QR Kód" (Generate QR Code) button.
4.  The QR code will appear on the left panel.
5.  Optionally, click "Stáhnout QR kód" (Download QR code) to save a PDF.
6.  The "i" button in the top-right corner can toggle the visibility of the raw QR string.

## Field Lengths (Based on SPD Standard)

* **Receiver Name (RN):** Max 35 characters
* **Amount (AM):** Max 10 characters (e.g., 9999999.99)
* **Message (MSG):** Max 60 characters
* **Variable, Constant, Specific Symbols (X-VS, X-KS, X-SS):** Max 10 digits each
* **Account Prefix:** Max 6 digits
* **Account Number:** Max 10 digits

**Disclaimer:**
Always verify the accuracy of the generated QR code and the data read by banking applications. Use this tool at your own risk.
