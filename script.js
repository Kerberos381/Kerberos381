document.addEventListener("DOMContentLoaded", function () {
    const qrCodeContainer = document.getElementById("qrcode");
    const generateBtn = document.getElementById("generateBtn");
    const downloadPdfLink = document.getElementById("downloadPdfLink");
    const qrStringOutput = document.getElementById("qrStringOutput");
    const infoButton = document.getElementById("infoButton");

    // Input fields
    const allInputs = {
        receiverName: document.getElementById("receiverName"),
        prefix: document.getElementById("prefix"),
        accountNumber: document.getElementById("accountNumber"),
        bankCode: document.getElementById("bankCode"),
        amount: document.getElementById("amount"),
        variableSymbol: document.getElementById("variableSymbol"),
        constantSymbol: document.getElementById("constantSymbol"),
        specificSymbol: document.getElementById("specificSymbol"),
        message: document.getElementById("message")
    };

    const initialQRText = "INFO: Vyplňte údaje a klikněte na 'Generovat QR Kód'";

    const characterMap = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i', 'ň': 'n',
        'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y', 'ž': 'z',
        'Á': 'A', 'Č': 'C', 'Ď': 'D', 'É': 'E', 'Ě': 'E', 'Í': 'I', 'Ň': 'N',
        'Ó': 'O', 'Ř': 'R', 'Š': 'S', 'Ť': 'T', 'Ú': 'U', 'Ů': 'U', 'Ý': 'Y', 'Ž': 'Z'
    };

    // Function to replace unsupported characters for QR code
    function replaceUnsupportedCharacters(text) {
        if (typeof text !== 'string') return ''; // Ensure text is a string
        return text.replace(/[^\x00-\x7F]/g, (char) => characterMap[char] || '');
    }

    // Function to validate and notify of unsupported characters (used before explicit generation)
    function validateTextForAlert(text) {
        if (typeof text !== 'string') return true; // Pass if not a string (e.g. empty)
        const unsupportedChars = text.match(/[^\x00-\x7F]/g) || [];
        const unsupported = unsupportedChars.filter(char => !characterMap[char]);
        if (unsupported.length > 0) {
            alert(`Některé zadané znaky nejsou přímo podporovány v QR kódu a budou nahrazeny nebo odstraněny: ${unsupported.join(", ")}. Zkontrolujte prosím výsledek.`);
        }
        return true;
    }
    
    // Helper function to apply animation classes to the QR code container
    function triggerQRCodeAnimation(animationClass) {
        qrCodeContainer.classList.remove('qr-code-enter', 'qr-code-update');
        // Force reflow to ensure animation restarts if the same class is re-added quickly
        void qrCodeContainer.offsetWidth; 
        if (animationClass) { // Only add class if one is provided
            qrCodeContainer.classList.add(animationClass);
        }
    }

    // Main function to generate and display the QR code
    function generateQRCode(text, animationType = 'update') { // animationType: 'enter', 'update', or 'none'
        qrCodeContainer.innerHTML = ""; // Clear previous QR code or placeholder

        // Apply animation based on type
        if (animationType === 'enter') {
            triggerQRCodeAnimation('qr-code-enter');
        } else if (animationType === 'update') {
            triggerQRCodeAnimation('qr-code-update');
        } else { 
            triggerQRCodeAnimation(null); // Remove any animation classes
        }

        // Determine QR code size, ensuring it fits within the container
        let qrCodeSize = 370; // Default desktop size
        if (window.innerWidth < 767) {
            qrCodeSize = Math.min(300, qrCodeContainer.offsetWidth > 20 ? qrCodeContainer.offsetWidth - 20 : 250);
        } else {
             qrCodeSize = Math.min(370, qrCodeContainer.offsetWidth > 40 ? qrCodeContainer.offsetWidth - 40 : 330);
        }
        // Ensure a minimum size if offsetWidth is 0 (e.g. if container is hidden initially)
        if (qrCodeSize <= 0) qrCodeSize = 250;


        // Create the QR code using the library
        new QRCode(qrCodeContainer, {
            text: text,
            width: qrCodeSize,
            height: qrCodeSize,
            colorDark: "#000000",
            colorLight: "#FFFFFF", // Solid white background for better scannability
            correctLevel: QRCode.CorrectLevel.M, // Standard error correction level
        });
        qrStringOutput.textContent = text; // Display the raw QR string
    }

    // Function to calculate Czech IBAN
    function calculateIBAN(bankCode, prefix, accountNumber, silent = false) {
        if (!bankCode || !accountNumber) {
            if (!silent) alert("Pro výpočet IBAN je nutné zadat číslo účtu a kód banky.");
            return null;
        }
        const paddedPrefix = (prefix || '').padStart(6, '0');
        const paddedAccountNumber = accountNumber.padStart(10, '0');
        const bban = `${bankCode}${paddedPrefix}${paddedAccountNumber}`;
        const numericIBAN = `${bban}123500`; // CZ -> 1235 (C=12, Z=35), 00 for checksum placeholder

        try {
            const checksumBigInt = 98n - (BigInt(numericIBAN) % 97n);
            let checkDigits = checksumBigInt.toString();
            if (checkDigits.length < 2) { // Ensure two digits for checksum
                checkDigits = '0' + checkDigits;
            }
            return `CZ${checkDigits}${bban}`;
        } catch (error) {
            if (!silent) { // Only show alert if not in silent mode (e.g., during live updates)
                console.error("Error calculating IBAN:", error, {bankCode, prefix, accountNumber, numericIBAN});
                alert("Nepodařilo se vypočítat IBAN. Zkontrolujte prosím zadané číslo účtu, předčíslí a kód banky. Ujistěte se, že obsahují pouze číslice.");
            }
            return null;
        }
    }

    // Function to generate the QR string, used for both live updates and final generation
    function generateQRStringForUpdate(data, silentValidation = false) {
        if (!data.accountNumber || !data.bankCode) { // Essential data for a payment QR
            return initialQRText; 
        }

        const iban = calculateIBAN(data.bankCode, data.prefix, data.accountNumber, silentValidation);
        if (!iban) {
            return initialQRText; // IBAN calculation failed
        }

        let amountStr = "0.00"; // Default to "0.00" for consistency
        if (data.amount && data.amount.trim() !== "") {
            const amountNum = parseFloat(data.amount.replace(',', '.')); // Allow comma as decimal separator
            if (!isNaN(amountNum)) {
                amountStr = amountNum.toFixed(2); // Ensure two decimal places
                if (amountNum < 0 || amountStr.length > 10 || amountNum > 9999999.99) { 
                    if (!silentValidation) alert("Částka je neplatná, záporná, nebo příliš vysoká (max 9 999 999.99 Kč).");
                    return initialQRText; 
                }
            } else {
                 if (!silentValidation) alert("Zadaná částka není platné číslo.");
                 return initialQRText; 
            }
        }

        // Construct the QR string
        let qrString = `SPD*1.0*ACC:${iban}*AM:${amountStr}*CC:CZK`;
        if (data.receiverName) qrString += `*RN:${replaceUnsupportedCharacters(data.receiverName)}`;
        if (data.variableSymbol) qrString += `*X-VS:${data.variableSymbol}`;
        if (data.constantSymbol) qrString += `*X-KS:${data.constantSymbol}`;
        if (data.specificSymbol) qrString += `*X-SS:${data.specificSymbol}`;
        if (data.message) qrString += `*MSG:${replaceUnsupportedCharacters(data.message)}`;
        qrString += `*PT:IP`; // Instant payment flag

        // Basic length check for QR code data
        if (qrString.length > 330) { // Adjusted practical limit for SPD QR codes
            if (!silentValidation) alert("Vyplněné údaje jsou příliš dlouhé pro QR kód. Zkuste zkrátit zprávu nebo název příjemce.");
            return initialQRText;
        }
        return qrString;
    }

    // Debounce utility function
    let debounceTimer;
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Function to handle live input changes and update QR
    function handleLiveInputChange() {
        const currentData = {
            receiverName: allInputs.receiverName.value,
            prefix: allInputs.prefix.value,
            accountNumber: allInputs.accountNumber.value,
            bankCode: allInputs.bankCode.value,
            amount: allInputs.amount.value,
            variableSymbol: allInputs.variableSymbol.value,
            constantSymbol: allInputs.constantSymbol.value,
            specificSymbol: allInputs.specificSymbol.value,
            message: allInputs.message.value
        };
        // Use silent validation for live updates to avoid spamming alerts
        const qrString = generateQRStringForUpdate(currentData, true); 
        generateQRCode(qrString, 'update'); // Use 'update' (qrFadeInOut) animation
    }

    const debouncedLiveUpdate = debounce(handleLiveInputChange, 450); // Adjusted debounce delay

    // Attach event listeners to all form inputs for live updates
    for (const key in allInputs) {
        if (allInputs.hasOwnProperty(key)) {
            const inputElement = allInputs[key];
            const eventType = (inputElement.tagName === 'SELECT') ? 'change' : 'input';
            inputElement.addEventListener(eventType, debouncedLiveUpdate);
        }
    }

    // Load bank codes and display initial QR code
    fetch('bank_codes.json')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            data.forEach(bank => {
                const option = document.createElement('option');
                option.value = bank.code;
                option.textContent = `${bank.name} (${bank.code})`;
                allInputs.bankCode.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading bank codes:', error);
            qrCodeContainer.innerHTML = '<p style="color:red; text-align:center; padding: 20px;">Chyba: Nepodařilo se načíst kódy bank. Funkčnost omezena.</p>';
        })
        .finally(() => {
            generateQRCode(initialQRText, 'enter'); // Display initial QR with 'enter' animation
        });

    // Event listener for the "Generate QR Kód" button
    generateBtn.addEventListener("click", function (event) {
        event.preventDefault(); // Prevent default form submission

        // Validate mandatory fields
        const mandatoryFieldsInfo = [
            { input: allInputs.accountNumber, name: "Číslo účtu" },
            { input: allInputs.bankCode, name: "Kód banky" },
        ];
        let allFieldsFilled = true;
        let missingFieldsMessages = [];

        mandatoryFieldsInfo.forEach(fieldInfo => {
            fieldInfo.input.style.border = "1px solid #ced4da"; // Reset style
            fieldInfo.input.style.boxShadow = "none"; // Reset style
            if (!fieldInfo.input.value.trim()) {
                fieldInfo.input.style.border = "1px solid #e74c3c"; // Error style
                fieldInfo.input.style.boxShadow = "0 0 0 0.2rem rgba(231, 76, 60, 0.25)"; // Error style
                allFieldsFilled = false;
                missingFieldsMessages.push(fieldInfo.name);
            }
        });

        if (!allFieldsFilled) {
            alert(`Prosím vyplňte povinná pole: ${missingFieldsMessages.join(", ")}`);
            mandatoryFieldsInfo.find(f => missingFieldsMessages.includes(f.name))?.input?.focus();
            generateQRCode(initialQRText, 'enter'); // Show initial QR if form validation fails
            return;
        }
        
        // Validate text fields for unsupported characters (with alerts)
        if (!validateTextForAlert(allInputs.receiverName.value) || !validateTextForAlert(allInputs.message.value)) {
            // Alert already shown by validateTextForAlert
        }
        
        const currentData = {
            receiverName: allInputs.receiverName.value,
            prefix: allInputs.prefix.value,
            accountNumber: allInputs.accountNumber.value,
            bankCode: allInputs.bankCode.value,
            amount: allInputs.amount.value,
            variableSymbol: allInputs.variableSymbol.value,
            constantSymbol: allInputs.constantSymbol.value,
            specificSymbol: allInputs.specificSymbol.value,
            message: allInputs.message.value
        };

        // Generate QR string with full validation (alerts enabled)
        const qrString = generateQRStringForUpdate(currentData, false); 
        
        if (qrString && qrString !== initialQRText) {
            generateQRCode(qrString, 'enter'); // Use 'enter' (bounceIn) animation for explicit generation
            if (window.innerWidth < 767) { // Scroll to QR on mobile
                 qrCodeContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } else {
            // If validation failed and generateQRStringForUpdate returned initialQRText, ensure it's displayed
            generateQRCode(initialQRText, 'enter'); 
        }
    });

    // Event listener for the info button
    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = (qrStringOutput.style.display === "none" || qrStringOutput.style.display === "") ? "block" : "none";
    });

    // Event listener for pasting into the account number field
    allInputs.accountNumber.addEventListener('paste', function (event) {
        event.preventDefault();
        const paste = (event.clipboardData || window.clipboardData).getData('text');
        parseAccountNumber(paste); // Parse and fill inputs
        debouncedLiveUpdate(); // Trigger live update after paste
    });
    
    // Function to parse pasted account string
    function parseAccountNumber(accountString) {
        const accountRegex = /^(?:(\d{0,6})-)?(\d{1,10})(?:\/(\d{4}))?$/;
        const match = accountString.match(accountRegex);
        if (match) {
            const [, prefix, accountNumber, bankCode] = match;
            allInputs.prefix.value = prefix || '';
            allInputs.accountNumber.value = accountNumber || '';
            if (bankCode) {
                const bankExists = Array.from(allInputs.bankCode.options).some(opt => opt.value === bankCode);
                if (bankExists) {
                    allInputs.bankCode.value = bankCode;
                } else {
                    alert(`Kód banky "${bankCode}" ze schránky nebyl nalezen v seznamu. Prosím vyberte kód banky manuálně.`);
                    allInputs.bankCode.value = ""; // Reset if not found
                }
            }
        } else {
            alert('Formát čísla účtu pro vložení není platný. Použijte např. 123456-1234567890/0100.');
        }
    }

    // Event listener for the download PDF link
    downloadPdfLink.addEventListener("click", function (event) {
        event.preventDefault();

        // Check if a valid payment QR is displayed
        if (qrStringOutput.textContent === initialQRText || !qrCodeContainer.querySelector("canvas")) {
            alert("Nejprve prosím vygenerujte platný platební QR kód vyplněním údajů.");
            return;
        }
        const qrCanvas = qrCodeContainer.querySelector("canvas");
        if (!qrCanvas) { // Should be redundant, but good for safety
            alert("QR kód není k dispozici pro stažení.");
            return;
        }

        const qrDataUrl = qrCanvas.toDataURL("image/png");
        
        // Gather current data for PDF
        const pdfData = { 
            receiverName: allInputs.receiverName.value,
            prefix: allInputs.prefix.value,
            accountNumber: allInputs.accountNumber.value,
            bankCodeDisplay: allInputs.bankCode.options[allInputs.bankCode.selectedIndex]?.text || allInputs.bankCode.value,
            amount: parseFloat(allInputs.amount.value.replace(',', '.') || "0").toFixed(2),
            variableSymbol: allInputs.variableSymbol.value,
            constantSymbol: allInputs.constantSymbol.value,
            specificSymbol: allInputs.specificSymbol.value,
            message: allInputs.message.value,
            // Calculate IBAN silently for PDF, as data should be valid by now
            iban: calculateIBAN(allInputs.bankCode.value, allInputs.prefix.value, allInputs.accountNumber.value, true) 
        };

        const dataFields = [
            { label: "Název příjemce", value: pdfData.receiverName },
            { label: "Předčíslí účtu", value: pdfData.prefix },
            { label: "Číslo účtu", value: pdfData.accountNumber },
            { label: "Kód banky", value: pdfData.bankCodeDisplay },
            { label: "Částka v Kč", value: pdfData.amount },
            { label: "IBAN", value: pdfData.iban },
            { label: "Variabilní symbol", value: pdfData.variableSymbol },
            { label: "Konstantní symbol", value: pdfData.constantSymbol },
            { label: "Specifický symbol", value: pdfData.specificSymbol },
            { label: "Zpráva pro příjemce", value: pdfData.message },
        ];

        const content = [
            { text: 'Platební QR Kód', style: 'header', alignment: 'center' },
            { image: qrDataUrl, width: 180, alignment: 'center', margin: [0, 0, 0, 20] }
        ];
        dataFields.forEach(field => {
            // Only add field to PDF if it has a non-empty value
            if (field.value && field.value.toString().trim() !== "") {
                content.push({
                    text: [{ text: `${field.label}: `, bold: true }, field.value.toString()],
                    fontSize: 10, margin: [0, 0, 0, 6]
                });
            }
        });
        content.push({
            text: 'UPOZORNĚNÍ: VŽDY ZKONTROLUJTE SPRÁVNOST NAČTENÝCH DAT VE VAŠÍ BANKOVNÍ APLIKACI.',
            style: 'disclaimerPdf', alignment: 'center', margin: [0, 20, 0, 0]
        });

        const docDefinition = {
            content: content, defaultStyle: { font: 'Roboto' }, // Roboto is a common pdfmake default
            styles: {
                header: { fontSize: 16, bold: true, margin: [0, 0, 0, 15] },
                disclaimerPdf: { fontSize: 8, italics: true, color: '#555555' }
            }
        };
        try {
            // Generate a more descriptive filename
            let fileName = 'platebni_qr_kod.pdf';
            const receiver = pdfData.receiverName.trim().replace(/[^a-z0-9]/gi, '_').toLowerCase();
            const amountVal = pdfData.amount.trim(); // Amount is already toFixed(2)
            if (receiver) {
                fileName = `${receiver}_${amountVal !== "0.00" ? amountVal : 'platba'}_qr.pdf`;
            } else if (amountVal !== "0.00") {
                 fileName = `platba_${amountVal}_qr.pdf`;
            }
            pdfMake.createPdf(docDefinition).download(fileName);
        } catch(e) {
            console.error("Error creating PDF: ", e);
            alert("Nepodařilo se vytvořit PDF. Zkontrolujte konzoli pro detaily.");
        }
    });
});
