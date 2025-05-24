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
    const constantSymbolInput = document.getElementById("constantSymbol");
    const specificSymbolInput = document.getElementById("specificSymbol");
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
            alert(`Nepodporované znaky byly detekovány a odstraněny/nahrazeny: ${unsupported.join(", ")}`);
            // Return true as they will be replaced/removed by replaceUnsupportedCharacters
        }
        return true; 
    }

    function setQrPlaceholder() {
        qrCodeContainer.innerHTML = '<p style="text-align:center; color:#777; margin-top: 50px;">Zde se zobrazí QR kód po zadání údajů.</p>';
         qrCodeContainer.style.animation = "none"; // Ensure no animation on placeholder
    }

    function generateQRCode(text) {
        qrCodeContainer.innerHTML = ""; // Clear previous QR code or placeholder

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
            colorLight: "#FFFFFF", // Changed from transparent to white
            correctLevel: QRCode.CorrectLevel.M,
        });

        qrStringOutput.textContent = text;
    }

    function calculateIBAN(bankCode, prefix, accountNumber) {
        const paddedPrefix = prefix.padStart(6, '0');
        const paddedAccountNumber = accountNumber.padStart(10, '0');
        const bban = `${bankCode}${paddedPrefix}${paddedAccountNumber}`;
        // Czech Republic's country code for IBAN calculation is CZ -> 1235
        const numericIBAN = `${bban}123500`; // 12 for C, 35 for Z, 00 for two check digits placeholder

        try {
            const checksum = 98n - BigInt(numericIBAN) % 97n;
            const checkDigits = checksum.toString().padStart(2, '0');
            // Ensure checkDigits are valid (e.g. 00-96 -> 98-02, so 01 is not possible, should be 97 - (n % 97))
            // The formula 98 - (val % 97) is standard. If checksum is 0 or 1, padStart makes it 00 or 01.
            // If checksum is, for example, 2, it becomes "02". If 97, it becomes "97".
             if (checkDigits === '00' || checkDigits === '01' || checkDigits === '99') { // Some values are invalid or rare
                // This is a very basic check, a full IBAN validation library would be more robust
                // For simplicity, we assume the math is correct as per standard.
            }
            return `CZ${checkDigits}${bban}`;
        } catch (error) {
            console.error("Error calculating IBAN:", error, "Input values:", {bankCode, prefix, accountNumber, numericIBAN});
            alert("Nepodařilo se vypočítat IBAN. Zkontrolujte prosím zadané číslo účtu, předčíslí a kód banky.");
            return null;
        }
    }

    function generateQRString(data) {
        const iban = calculateIBAN(data.bankCode, data.prefix || '', data.accountNumber); // Allow empty prefix, calculateIBAN handles padding
        if (!iban) return null;

        let qrString = `SPD*1.0*ACC:${iban}*AM:${data.amount || "0"}*CC:CZK`; // Ensure amount is present

        if (data.receiverName) qrString += `*RN:${data.receiverName}`;
        if (data.variableSymbol) qrString += `*X-VS:${data.variableSymbol}`;
        if (data.constantSymbol) qrString += `*X-KS:${data.constantSymbol}`; 
        if (data.specificSymbol) qrString += `*X-SS:${data.specificSymbol}`; 
        if (data.message) qrString += `*MSG:${data.message}`;

        // Include the payment type as instant payment
        qrString += `*PT:IP`;

        return qrString;
    }

    // Load bank codes from JSON file and populate the dropdown
    fetch('bank_codes.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
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
            alert('Nepodařilo se načíst seznam kódů bank. Některé funkce nemusí být dostupné.');
        });

    // Set initial placeholder for QR code area
    setQrPlaceholder();
    // Removed: generateQRCode("HELLO STRANGER"); 

    generateBtn.addEventListener("click", function (event) {
        event.preventDefault();

        const mandatoryFields = [
            { id: "accountNumber", name: "Číslo účtu" },
            { id: "bankCode", name: "Kód banky", element: bankCodeSelect },
        ];
        let allFieldsFilled = true;
        let missingFields = [];

        // Reset input styles
        mandatoryFields.forEach(fieldInfo => {
            const inputElement = fieldInfo.element || document.getElementById(fieldInfo.id);
            inputElement.style.border = "none"; // Reset to default from CSS
            inputElement.style.boxShadow = "0 2px 3px rgba(0, 0, 0, 0.1)"; // Reset to default from CSS
        });

        // Validate mandatory fields
        mandatoryFields.forEach(fieldInfo => {
            const inputElement = fieldInfo.element || document.getElementById(fieldInfo.id);
            if (!inputElement.value.trim()) {
                inputElement.style.border = "1px solid red";
                inputElement.style.boxShadow = "0 0 5px rgba(255, 0, 0, 0.5)";
                allFieldsFilled = false;
                missingFields.push(fieldInfo.name);
            }
        });

        if (!allFieldsFilled) {
            alert(`Prosím vyplňte povinná pole!: ${missingFields.join(", ")}`);
            // Focus the first missing field
            const firstMissingFieldId = mandatoryFields.find(f => missingFields.includes(f.name))?.id;
            if (firstMissingFieldId) {
                document.getElementById(firstMissingFieldId)?.focus();
            }
            return;
        }

        let data = {
            receiverName: receiverNameInput.value || "",
            prefix: prefixInput.value || "", // prefix can be empty, IBAN calculation will pad
            accountNumber: accountNumberInput.value,
            bankCode: bankCodeSelect.value,
            variableSymbol: variableSymbolInput.value,
            constantSymbol: constantSymbolInput.value,
            specificSymbol: specificSymbolInput.value,
            message: messageInput.value,
            amount: amountInput.value || "0" // Default amount to 0 if empty
        };

        // Replace unsupported characters in receiverName and message for QR code
        // ValidateText is called first to inform user, then replaceUnsupportedCharacters cleans the string
        if (!validateText(data.receiverName) || !validateText(data.message)) {
            // Though validateText currently always returns true after alert,
            // this structure allows for future change where it might return false to stop execution.
        }
        data.receiverName = replaceUnsupportedCharacters(data.receiverName);
        data.message = replaceUnsupportedCharacters(data.message);


        const qrString = generateQRString(data);
        if (qrString) {
            generateQRCode(qrString);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
             setQrPlaceholder(); // If QR string generation fails (e.g. IBAN calc error), show placeholder
        }
    });

    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = qrStringOutput.style.display === "none" ? "block" : "none";
    });

    accountNumberInput.addEventListener('paste', function (event) {
        event.preventDefault();
        const paste = (event.clipboardData || window.clipboardData).getData('text');
        parseAccountNumber(paste);
    });

    function parseAccountNumber(accountString) {
        const accountRegex = /^(?:(\d{0,6})-)?(\d{1,10})(?:\/(\d{4}))?$/;
        const match = accountString.match(accountRegex);

        if (match) {
            const [, prefix, accountNumber, bankCode] = match;
            prefixInput.value = prefix || '';
            accountNumberInput.value = accountNumber || '';
            if (bankCode) {
                bankCodeSelect.value = bankCode;
            }
        } else {
            alert('Formát čísla účtu pro vložení není platný. Použijte formát PREDČISLI-CISLO/KODBANKY, PREDČISLI-CISLO, CISLO/KODBANKY nebo jen CISLO.');
        }
    }

    downloadPdfLink.addEventListener("click", function (event) {
        event.preventDefault();

        const qrCanvas = qrCodeContainer.querySelector("canvas");
        if (!qrCanvas) {
            alert("Nejprve prosím vygenerujte QR kód kliknutím na tlačítko 'Generovat QR Kód'.");
            return;
        }

        const qrDataUrl = qrCanvas.toDataURL("image/png");

        const dataFields = [
            { label: "Název příjemce", value: receiverNameInput.value },
            { label: "Předčíslí účtu", value: prefixInput.value },
            { label: "Číslo účtu", value: accountNumberInput.value },
            { label: "Kód banky", value: bankCodeSelect.options[bankCodeSelect.selectedIndex].text },
            { label: "Částka v Kč", value: amountInput.value || "0" },
            { label: "Variabilní symbol", value: variableSymbolInput.value },
            { label: "Konstantní symbol", value: constantSymbolInput.value },
            { label: "Specifický symbol", value: specificSymbolInput.value },
            { label: "Zpráva pro příjemce", value: messageInput.value },
        ];

        const content = [];
        content.push({
            text: 'Platební QR Kód',
            style: 'header',
            alignment: 'center'
        });
        content.push({
            image: qrDataUrl,
            width: 200, // Increased size for better readability in PDF
            alignment: 'center',
            margin: [0, 0, 0, 20] // Top, Right, Bottom, Left
        });

        dataFields.forEach(field => {
            if (field.value.trim() !== "") { // Only add fields that have a value
                content.push({
                    text: [
                        { text: `${field.label}: `, bold: true },
                        field.value
                    ],
                    fontSize: 11, // Slightly smaller for more content
                    margin: [0, 0, 0, 5]
                });
            }
        });
         content.push({
            text: 'UPOZORNĚNÍ: VŽDY ZKONTROLUJTE SPRÁVNOST NAČTENÝCH DAT VE VAŠÍ BANKOVNÍ APLIKACI.',
            style: 'disclaimer',
            alignment: 'center',
            margin: [0, 20, 0, 0]
        });


        const docDefinition = {
            content: content,
            defaultStyle: {
                // font: 'Helvetica' // pdfmake default is Roboto, ensure vfs_fonts includes Helvetica or use a standard one
            },
            styles: {
                header: {
                    fontSize: 18,
                    bold: true,
                    margin: [0, 0, 0, 15]
                },
                 disclaimer: {
                    fontSize: 9,
                    italics: true,
                    color: 'gray'
                }
            }
        };

        try {
            pdfMake.createPdf(docDefinition).download('platebni_qr_kod.pdf');
        } catch(e) {
            console.error("Error creating PDF: ", e);
            alert("Nepodařilo se vytvořit PDF. Zkontrolujte konzoli pro detaily.");
        }
    });
});
