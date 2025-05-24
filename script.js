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

    function replaceUnsupportedCharacters(text) {
        if (typeof text !== 'string') return '';
        return text.replace(/[^\x00-\x7F]/g, (char) => characterMap[char] || '');
    }

    function validateTextForAlert(text) { // Renamed to distinguish from silent validation
        if (typeof text !== 'string') return true;
        const unsupportedChars = text.match(/[^\x00-\x7F]/g) || [];
        const unsupported = unsupportedChars.filter(char => !characterMap[char]);
        if (unsupported.length > 0) {
            alert(`Některé zadané znaky nejsou přímo podporovány v QR kódu a budou nahrazeny nebo odstraněny: ${unsupported.join(", ")}. Zkontrolujte prosím výsledek.`);
        }
        return true;
    }

    function generateQRCode(text, isInitial = false) {
        qrCodeContainer.innerHTML = "";
        qrCodeContainer.style.animation = "none";
        
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                // Only apply bounceIn if it's not the silent initial placeholder or an error placeholder
                if (!isInitial && text !== initialQRText) {
                    qrCodeContainer.style.animation = "bounceIn 1s ease";
                } else if (isInitial) { // Or if it's the very first load
                     qrCodeContainer.style.animation = "bounceIn 1s ease";
                }
            });
        });

        const qrCodeSize = window.innerWidth < 767 ? Math.min(300, qrCodeContainer.offsetWidth > 0 ? qrCodeContainer.offsetWidth - 20 : 280) : 370;

        new QRCode(qrCodeContainer, {
            text: text,
            width: qrCodeSize,
            height: qrCodeSize,
            colorDark: "#000000",
            colorLight: "#FFFFFF",
            correctLevel: QRCode.CorrectLevel.M,
        });
        qrStringOutput.textContent = text;
    }

    function calculateIBAN(bankCode, prefix, accountNumber, silent = false) {
        if (!bankCode || !accountNumber) {
            if (!silent) alert("Pro výpočet IBAN je nutné zadat číslo účtu a kód banky.");
            return null;
        }
        const paddedPrefix = (prefix || '').padStart(6, '0');
        const paddedAccountNumber = accountNumber.padStart(10, '0');
        const bban = `${bankCode}${paddedPrefix}${paddedAccountNumber}`;
        const numericIBAN = `${bban}123500`;

        try {
            const checksumBigInt = 98n - (BigInt(numericIBAN) % 97n);
            let checkDigits = checksumBigInt.toString();
            if (checkDigits.length < 2) {
                checkDigits = '0' + checkDigits;
            }
            return `CZ${checkDigits}${bban}`;
        } catch (error) {
            if (!silent) {
                console.error("Error calculating IBAN:", error, {bankCode, prefix, accountNumber, numericIBAN});
                alert("Nepodařilo se vypočítat IBAN. Zkontrolujte prosím zadané číslo účtu, předčíslí a kód banky. Ujistěte se, že obsahují pouze číslice.");
            }
            return null;
        }
    }

    function generateQRStringForLiveUpdate(data, silentValidation = false) {
        // For live updates, we need at least account number and bank code for a meaningful attempt
        if (!data.accountNumber || !data.bankCode) {
            return initialQRText; // Not enough data for a payment QR, show initial
        }

        const iban = calculateIBAN(data.bankCode, data.prefix, data.accountNumber, silentValidation);
        if (!iban) {
            return initialQRText; // IBAN calculation failed (possibly due to partial input)
        }

        let amountStr = "0";
        if (data.amount) {
            const amountNum = parseFloat(data.amount);
            if (!isNaN(amountNum)) {
                amountStr = amountNum.toFixed(2);
                if (amountStr.length > 10 || amountNum > 9999999.99) { // Max 10 chars (e.g. 9999999.99)
                    if (!silentValidation) alert("Částka je příliš vysoká nebo neplatná.");
                    return initialQRText; // Amount too high or invalid
                }
            } else {
                 if (!silentValidation && data.amount.trim() !== "") alert("Zadaná částka není platné číslo.");
                 return initialQRText; // Invalid amount if not empty
            }
        }

        let qrString = `SPD*1.0*ACC:${iban}*AM:${amountStr}*CC:CZK`;
        if (data.receiverName) qrString += `*RN:${replaceUnsupportedCharacters(data.receiverName)}`;
        if (data.variableSymbol) qrString += `*X-VS:${data.variableSymbol}`;
        if (data.constantSymbol) qrString += `*X-KS:${data.constantSymbol}`;
        if (data.specificSymbol) qrString += `*X-SS:${data.specificSymbol}`;
        if (data.message) qrString += `*MSG:${replaceUnsupportedCharacters(data.message)}`;
        qrString += `*PT:IP`;

        if (qrString.length > 300) { // Basic length check
            if (!silentValidation) alert("Vyplněné údaje jsou příliš dlouhé pro QR kód.");
            return initialQRText;
        }
        return qrString;
    }


    // Debounce function:
    let debounceTimer;
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Function to be called on input events
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
        const qrString = generateQRStringForLiveUpdate(currentData, true);
        generateQRCode(qrString);
    }

    const debouncedLiveUpdate = debounce(handleLiveInputChange, 400); // 400ms delay

    // Attach event listeners to all inputs
    for (const key in allInputs) {
        if (allInputs.hasOwnProperty(key)) {
            const inputElement = allInputs[key];
            if (inputElement.tagName === 'SELECT') {
                inputElement.addEventListener('change', debouncedLiveUpdate);
            } else {
                inputElement.addEventListener('input', debouncedLiveUpdate);
            }
        }
    }

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
            qrCodeContainer.innerHTML = '<p style="color:red; text-align:center;">Chyba: Nepodařilo se načíst kódy bank.</p>';
        })
        .finally(() => {
            generateQRCode(initialQRText, true); // Pass true for isInitial
        });

    generateBtn.addEventListener("click", function (event) {
        event.preventDefault();

        const mandatoryFieldsInfo = [
            { input: allInputs.accountNumber, name: "Číslo účtu" },
            { input: allInputs.bankCode, name: "Kód banky" },
        ];
        let allFieldsFilled = true;
        let missingFieldsMessages = [];

        mandatoryFieldsInfo.forEach(fieldInfo => {
            fieldInfo.input.style.border = "1px solid #ced4da";
            fieldInfo.input.style.boxShadow = "none";
            if (!fieldInfo.input.value.trim()) {
                fieldInfo.input.style.border = "1px solid #e74c3c";
                fieldInfo.input.style.boxShadow = "0 0 0 0.2rem rgba(231, 76, 60, 0.25)";
                allFieldsFilled = false;
                missingFieldsMessages.push(fieldInfo.name);
            }
        });

        if (!allFieldsFilled) {
            alert(`Prosím vyplňte povinná pole: ${missingFieldsMessages.join(", ")}`);
            mandatoryFieldsInfo.find(f => missingFieldsMessages.includes(f.name))?.input?.focus();
            generateQRCode(initialQRText); // Revert to initial if validation fails
            return;
        }

        // Perform full validation with alerts before final generation
        if (!validateTextForAlert(allInputs.receiverName.value) || !validateTextForAlert(allInputs.message.value)) {
            // Already alerted
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

        // Use the more stringent generateQRStringForLiveUpdate but with silentValidation = false to get alerts
        const qrString = generateQRStringForLiveUpdate(currentData, false); 
        
        if (qrString && qrString !== initialQRText) {
            generateQRCode(qrString);
            if (window.innerWidth < 767) {
                 qrCodeContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } else {
            // If qrString is initialQRText, it means some validation failed in generateQRStringForLiveUpdate
            // and an alert was likely shown. Ensure the initialQR is displayed.
            generateQRCode(initialQRText);
        }
    });

    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = qrStringOutput.style.display === "none" || qrStringOutput.style.display === "" ? "block" : "none";
    });

    allInputs.accountNumber.addEventListener('paste', function (event) {
        event.preventDefault();
        const paste = (event.clipboardData || window.clipboardData).getData('text');
        parseAccountNumber(paste);
        debouncedLiveUpdate(); // Trigger update after paste
    });

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
                    allInputs.bankCode.value = "";
                }
            }
        } else {
            alert('Formát čísla účtu pro vložení není platný...');
        }
    }

    downloadPdfLink.addEventListener("click", function (event) {
        event.preventDefault();
        if (qrStringOutput.textContent === initialQRText || !qrCodeContainer.querySelector("canvas")) {
            alert("Nejprve prosím vygenerujte platný platební QR kód vyplněním údajů.");
            return;
        }
        const qrCanvas = qrCodeContainer.querySelector("canvas");
        if (!qrCanvas) return;

        const qrDataUrl = qrCanvas.toDataURL("image/png");
        const pdfData = { // Gather data for PDF at the moment of download
            receiverName: allInputs.receiverName.value,
            prefix: allInputs.prefix.value,
            accountNumber: allInputs.accountNumber.value,
            bankCode: allInputs.bankCode.options[allInputs.bankCode.selectedIndex]?.text || allInputs.bankCode.value,
            amount: parseFloat(allInputs.amount.value || "0").toFixed(2),
            variableSymbol: allInputs.variableSymbol.value,
            constantSymbol: allInputs.constantSymbol.value,
            specificSymbol: allInputs.specificSymbol.value,
            message: allInputs.message.value,
            iban: calculateIBAN(allInputs.bankCode.value, allInputs.prefix.value, allInputs.accountNumber.value, true) // silent for PDF
        };

        const dataFields = [
            { label: "Název příjemce", value: pdfData.receiverName },
            { label: "Předčíslí účtu", value: pdfData.prefix },
            { label: "Číslo účtu", value: pdfData.accountNumber },
            { label: "Kód banky", value: pdfData.bankCode },
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
            content: content, defaultStyle: { font: 'Roboto' },
            styles: {
                header: { fontSize: 16, bold: true, margin: [0, 0, 0, 15] },
                disclaimerPdf: { fontSize: 8, italics: true, color: '#555555' }
            }
        };
        try {
            let fileName = 'platebni_qr_kod.pdf';
            const receiver = pdfData.receiverName.trim().replace(/[^a-z0-9]/gi, '_').toLowerCase();
            const amountVal = pdfData.amount.trim();
            if (receiver) fileName = `${receiver}_${amountVal || 'platba'}_qr.pdf`;
            else if (amountVal && amountVal !== "0.00") fileName = `platba_${amountVal}_qr.pdf`;
            pdfMake.createPdf(docDefinition).download(fileName);
        } catch(e) {
            console.error("Error creating PDF: ", e);
            alert("Nepodařilo se vytvořit PDF.");
        }
    });
});
