document.addEventListener("DOMContentLoaded", function () {
    const qrCodeContainer = document.getElementById("qrcode");
    const generateBtn = document.getElementById("generateBtn");
    const downloadPdfLink = document.getElementById("downloadPdfLink");
    const qrStringOutput = document.getElementById("qrStringOutput");
    const infoButton = document.getElementById("infoButton");

    // Input fields
    const receiverNameInput = document.getElementById("receiverName");
    const prefixInput = document.getElementById("prefix");
    const accountNumberInput = document.getElementById("accountNumber");
    const bankCodeSelect = document.getElementById("bankCode");
    const variableSymbolInput = document.getElementById("variableSymbol");
    const constantSymbolInput = document.getElementById("constantSymbol"); // New
    const specificSymbolInput = document.getElementById("specificSymbol"); // New
    const messageInput = document.getElementById("message");
    const amountInput = document.getElementById("amount");

    // Map of special characters to replacements (for QR code generation)
    const characterMap = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i', 'ň': 'n',
        'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y', 'ž': 'z',
        'Á': 'A', 'Č': 'C', 'Ď': 'D', 'É': 'E', 'Ě': 'E', 'Í': 'I', 'Ň': 'N',
        'Ó': 'O', 'Ř': 'R', 'Š': 'S', 'Ť': 'T', 'Ú': 'U', 'Ů': 'U', 'Ý': 'Y', 'Ž': 'Z'
    };

    // Function to replace unsupported characters for QR code
    function replaceUnsupportedCharacters(text) {
        return text.replace(/[^\x00-\x7F]/g, (char) => characterMap[char] || '');
    }

    // Function to validate and notify of unsupported characters
    function validateText(text) {
        const unsupportedChars = text.match(/[^\x00-\x7F]/g) || [];
        const unsupported = unsupportedChars.filter(char => !characterMap[char]);

        if (unsupported.length > 0) {
            alert(`Nepodporované znaky byly detekovány: ${unsupported.join(", ")}`);
            return false;
        }
        return true;
    }

    function generateQRCode(text) {
        qrCodeContainer.innerHTML = ""; // Clear previous QR code

        // Reset animation
        qrCodeContainer.style.animation = "none";
        void qrCodeContainer.offsetWidth; // Trigger reflow to reset animation
        qrCodeContainer.style.animation = "bounceIn 1s ease";

        const qrCodeSize = window.innerWidth < 768 ? 250 : 370;

        new QRCode(qrCodeContainer, {
            text: text,
            width: qrCodeSize,
            height: qrCodeSize,
            colorDark: "#000000",
            colorLight: "transparent",
            correctLevel: QRCode.CorrectLevel.M,
        });

        qrStringOutput.textContent = text;
    }

    function calculateIBAN(bankCode, prefix, accountNumber) {
        const paddedPrefix = prefix.padStart(6, '0');
        const paddedAccountNumber = accountNumber.padStart(10, '0');
        const bban = `${bankCode}${paddedPrefix}${paddedAccountNumber}`;
        const numericIBAN = `${bban}123500`;

        try {
            const checksum = 98n - BigInt(numericIBAN) % 97n;
            const checkDigits = checksum.toString().padStart(2, '0');
            return `CZ${checkDigits}${bban}`;
        } catch (error) {
            console.error("Error calculating IBAN:", error);
            alert("Nepodařilo se vypočítat IBAN. Zkontrolujte prosím své údaje.");
            return null;
        }
    }

    function generateQRString(data) {
        const iban = calculateIBAN(data.bankCode, data.prefix || '000000', data.accountNumber);
        if (!iban) return null;

        let qrString = `SPD*1.0*ACC:${iban}*AM:${data.amount}*CC:CZK`;

        if (data.receiverName) qrString += `*RN:${data.receiverName}`;
        if (data.variableSymbol) qrString += `*X-VS:${data.variableSymbol}`;
        if (data.constantSymbol) qrString += `*X-KS:${data.constantSymbol}`; // New
        if (data.specificSymbol) qrString += `*X-SS:${data.specificSymbol}`; // New
        if (data.message) qrString += `*MSG:${data.message}`;

        // Include the payment type as instant payment
        qrString += `*PT:IP`;

        return qrString;
    }

    // Load bank codes from JSON file and populate the dropdown
    fetch('bank_codes.json')
        .then(response => response.json())
        .then(data => {
            data.forEach(bank => {
                const option = document.createElement('option');
                option.value = bank.code;
                option.textContent = `${bank.name} (${bank.code})`;
                bankCodeSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading bank codes:', error);
            alert('Nepodařilo se načíst seznam kódů bank.');
        });

    // Initial QR code
    generateQRCode("HELLO STRANGER");

    generateBtn.addEventListener("click", function (event) {
        event.preventDefault();

        const mandatoryFields = [
            { id: "accountNumber", name: "Číslo účtu" },
            { id: "bankCode", name: "Kód banky", element: bankCodeSelect },
        ];
        let allFieldsFilled = true;
        let missingFields = [];

        // Reset input styles
        mandatoryFields.forEach(field => {
            const input = field.element || document.getElementById(field.id);
            input.style.border = "none";
            input.style.boxShadow = "0 2px 3px rgba(0, 0, 0, 0.1)";
        });

        // Validate mandatory fields
        mandatoryFields.forEach(field => {
            const input = field.element || document.getElementById(field.id);
            if (!input.value.trim()) {
                input.style.border = "1px solid red";
                input.style.boxShadow = "0 0 5px rgba(255, 0, 0, 0.5)";
                allFieldsFilled = false;
                missingFields.push(field.name);
            }
        });

        if (!allFieldsFilled) {
            alert(`Prosím vyplňte povinná pole!: ${missingFields.join(", ")}`);
            return;
        }

        let data = {
            receiverName: receiverNameInput.value || "",
            prefix: prefixInput.value || "",
            accountNumber: accountNumberInput.value,
            bankCode: bankCodeSelect.value,
            variableSymbol: variableSymbolInput.value,
            constantSymbol: constantSymbolInput.value, // New
            specificSymbol: specificSymbolInput.value, // New
            message: messageInput.value,
            amount: amountInput.value || "0"
        };

        // Replace unsupported characters in receiverName and message for QR code
        data.receiverName = replaceUnsupportedCharacters(data.receiverName);
        data.message = replaceUnsupportedCharacters(data.message);

        // Validate if any truly unsupported characters remain
        if (!validateText(data.receiverName) || !validateText(data.message)) {
            return;
        }

        const qrString = generateQRString(data);
        if (qrString) {
            generateQRCode(qrString);
            // Smooth scrolling to the top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });

    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = qrStringOutput.style.display === "none" ? "block" : "none";
    });

    // Paste event listener for account number input
    accountNumberInput.addEventListener('paste', function (event) {
        event.preventDefault();

        // Get pasted content
        const paste = (event.clipboardData || window.clipboardData).getData('text');
        parseAccountNumber(paste);
    });

    // Function to parse account number
    function parseAccountNumber(accountString) {
        // Regular expression to match account number formats
        const accountRegex = /^(?:(\d{0,6})-)?(\d{1,10})(?:\/(\d{4}))?$/;

        const match = accountString.match(accountRegex);

        if (match) {
            const [, prefix, accountNumber, bankCode] = match;

            if (prefix) {
                prefixInput.value = prefix;
            } else {
                prefixInput.value = '';
            }

            accountNumberInput.value = accountNumber;

            if (bankCode) {
                bankCodeSelect.value = bankCode;
            }
        } else {
            alert('Formát čísla účtu není platný.');
        }
    }

    // Download PDF functionality using pdfmake
    downloadPdfLink.addEventListener("click", function (event) {
        event.preventDefault();

        // Get the QR code image data
        const qrCanvas = qrCodeContainer.querySelector("canvas");
        if (!qrCanvas) {
            alert("Nejprve prosím vygenerujte QR kód.");
            return;
        }

        const qrDataUrl = qrCanvas.toDataURL("image/png");

        // Prepare the data to display
        const dataFields = [
            { label: "Název příjemce", value: receiverNameInput.value },
            { label: "Předčíslí účtu", value: prefixInput.value },
            { label: "Číslo účtu", value: accountNumberInput.value },
            { label: "Kód banky", value: bankCodeSelect.options[bankCodeSelect.selectedIndex].text },
            { label: "Částka v Kč", value: amountInput.value },
            { label: "Variabilní symbol", value: variableSymbolInput.value },
            { label: "Konstantní symbol", value: constantSymbolInput.value }, // New
            { label: "Specifický symbol", value: specificSymbolInput.value }, // New
            { label: "Zpráva pro příjemce", value: messageInput.value },
        ];

        const content = [];

        // Add the QR code image
        content.push({
            image: qrDataUrl,
            width: 200,
            alignment: 'center',
            margin: [0, 0, 0, 20]
        });

        // Add the data fields
        dataFields.forEach(field => {
            if (field.value) {
                content.push({
                    text: `${field.label}: ${field.value}`,
                    fontSize: 12,
                    margin: [0, 0, 0, 5]
                });
            }
        });

        // Define the PDF document
        const docDefinition = {
            content: content,
            defaultStyle: {
                font: 'Helvetica'
            },
            styles: {
                header: {
                    fontSize: 18,
                    bold: true,
                    margin: [0, 0, 0, 10]
                }
            }
        };

        // Generate the PDF
        pdfMake.createPdf(docDefinition).download('qr_code.pdf');
    });
});