document.addEventListener("DOMContentLoaded", function () {
    const qrCodeContainer = document.getElementById("qrcode");
    const generateBtn = document.getElementById("generateBtn");
    const qrStringOutput = document.getElementById("qrStringOutput");
    const infoButton = document.getElementById("infoButton");

    // Function to generate a QR code with responsive sizing
    function generateQRCode(text) {
        qrCodeContainer.innerHTML = ""; // Clear previous QR code

        // Reset animation
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

        // Show the generated QR code string for debugging
        qrStringOutput.textContent = text;
    }

    // Function to calculate Czech IBAN based on bank code, prefix, and account number
    function calculateIBAN(bankCode, prefix, accountNumber) {
        // Ensure prefix and account number have correct lengths
        const paddedPrefix = prefix.padStart(6, '0');
        const paddedAccountNumber = accountNumber.padStart(10, '0');

        // Assemble the BBAN part (bankCode + prefix + accountNumber)
        const bban = `${bankCode}${paddedPrefix}${paddedAccountNumber}`;

        // Convert to a numeric IBAN format by appending 'CZ' as '123500'
        const numericIBAN = `${bban}123500`;
        
        try {
            // Calculate checksum
            const checksum = 98n - BigInt(numericIBAN) % 97n;
            const checkDigits = checksum.toString().padStart(2, '0');

            // Return formatted IBAN
            return `CZ${checkDigits}${bban}`;
        } catch (error) {
            console.error("Error calculating IBAN:", error);
            alert("Failed to calculate IBAN. Please check your input.");
            return null;
        }
    }

    // Function to generate the QR code string in Czech payment format
    function generateQRString(data) {
        const iban = calculateIBAN(data.bankCode, data.prefix || '000000', data.accountNumber);

        // Ensure the IBAN is valid
        if (!iban) {
            return null; // Return null if IBAN calculation failed
        }

        // Start with mandatory fields
        let qrString = `SPD*1.0*ACC:${iban}*AM:${data.amount}*CC:CZK`;

        // Add optional fields if they are present
        if (data.receiverName) qrString += `*RN:${data.receiverName}`;
        if (data.variableSymbol) qrString += `*X-VS:${data.variableSymbol}`;
        if (data.message) qrString += `*MSG:${data.message}`;

        return qrString;
    }

    // Generate a default QR code on page load
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

        const data = {
            receiverName: document.getElementById("receiverName").value || "", // Get recipient name
            prefix: document.getElementById("prefix").value || "",
            accountNumber: document.getElementById("accountNumber").value,
            bankCode: document.getElementById("bankCode").value,
            variableSymbol: document.getElementById("variableSymbol").value,
            message: document.getElementById("message").value,
            amount: document.getElementById("amount").value || "0"
        };

        const qrString = generateQRString(data);
        if (qrString) {
            generateQRCode(qrString);
        }
    });

    // Toggle the visibility of the QR string output when the "i" button is clicked
    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = qrStringOutput.style.display === "none" ? "block" : "none";
    });
});