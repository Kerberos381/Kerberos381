document.addEventListener("DOMContentLoaded", function () {
    const qrCodeContainer = document.getElementById("qrcode");
    const generateBtn = document.getElementById("generateBtn");
    const qrStringOutput = document.getElementById("qrStringOutput");
    const infoButton = document.getElementById("infoButton");

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
            alert(`Unsupported characters detected: ${unsupported.join(", ")}`);
            return false;
        }
        return true;
    }

    function generateQRCode(text) {
        qrCodeContainer.innerHTML = ""; // Clear previous QR code

        qrCodeContainer.style.animation = "none";
        setTimeout(() => qrCodeContainer.style.animation = "zoomBounce 0.8s ease-out", 10);

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
            alert("Failed to calculate IBAN. Please check your input.");
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

        return qrString;
    }

    generateQRCode("HELLO STRANGER");

    generateBtn.addEventListener("click", function (event) {
        event.preventDefault();

        const mandatoryFields = [
            { id: "accountNumber", name: "Číslo účtu" },
            { id: "bankCode", name: "Kód Banky" },
        ];
        let allFieldsFilled = true;
        let missingFields = [];

        mandatoryFields.forEach(field => {
            const input = document.getElementById(field.id);
            input.style.border = "none";
            input.style.boxShadow = "0 2px 5px rgba(0, 0, 0, 0.1)";
        });

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
            receiverName: document.getElementById("receiverName").value || "",
            prefix: document.getElementById("prefix").value || "",
            accountNumber: document.getElementById("accountNumber").value,
            bankCode: document.getElementById("bankCode").value,
            variableSymbol: document.getElementById("variableSymbol").value,
            message: document.getElementById("message").value,
            amount: document.getElementById("amount").value || "0"
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
            window.scrollTo(0, 0);
            // Scroll to #root

        }
    });

    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = qrStringOutput.style.display === "none" ? "block" : "none";
    });
});