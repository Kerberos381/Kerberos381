document.addEventListener("DOMContentLoaded", function () {
    const qrCodeContainer = document.getElementById("qrcode");
    const generateBtn = document.getElementById("generateBtn");
    const qrStringOutput = document.getElementById("qrStringOutput");
    const infoButton = document.getElementById("infoButton");

    // Input fields
    const receiverNameInput = document.getElementById("receiverName");
    const prefixInput = document.getElementById("prefix");
    const accountNumberInput = document.getElementById("accountNumber");
    const bankCodeInput = document.getElementById("bankCode");
    const variableSymbolInput = document.getElementById("variableSymbol");
    const messageInput = document.getElementById("message");
    const amountInput = document.getElementById("amount");

    // Map of special characters to replacements
    const characterMap = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i', 'ň': 'n',
        'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y', 'ž': 'z'
    };

    // Function to replace unsupported characters
    function replaceUnsupportedCharacters(text) {
        return text.replace(/[^\w\s]/g, (char) => characterMap[char] || char);
    }

    // Function to validate and notify of unsupported characters
    function validateText(text) {
        const unsupportedChars = text.match(/[^\w\s]/g) || [];
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
        if (data.message) qrString += `*MSG:${data.message}`;

        // Include the payment type as instant payment
        qrString += `*PT:IP`;

        return qrString;
    }

    // Initial QR code
    generateQRCode("HELLO STRANGER");

    generateBtn.addEventListener("click", function (event) {
        event.preventDefault();

        const mandatoryFields = [
            { id: "accountNumber", name: "Číslo účtu" },
            { id: "bankCode", name: "Kód banky" },
        ];
        let allFieldsFilled = true;
        let missingFields = [];

        // Reset input styles
        mandatoryFields.forEach(field => {
            const input = document.getElementById(field.id);
            input.style.border = "none";
            input.style.boxShadow = "0 2px 3px rgba(0, 0, 0, 0.1)";
        });

        // Validate mandatory fields
        mandatoryFields.forEach(field => {
            const input = document.getElementById(field.id);
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
            bankCode: bankCodeInput.value,
            variableSymbol: variableSymbolInput.value,
            message: messageInput.value,
            amount: amountInput.value || "0"
        };

        // Replace unsupported characters in receiverName and message
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

    // Function to show error messages
    function showError(inputId, message) {
        const inputField = document.getElementById(inputId);
        let errorElement = inputField.nextElementSibling;

        if (!errorElement || !errorElement.classList.contains('error-message')) {
            errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            inputField.parentNode.insertBefore(errorElement, inputField.nextSibling);
        }

        errorElement.textContent = message;
    }

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
                bankCodeInput.value = bankCode;
            }
        } else {
            alert('Formát čísla účtu není platný.');
        }
    }
});