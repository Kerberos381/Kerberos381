document.addEventListener("DOMContentLoaded", function () {
    const qrCodeContainer = document.getElementById("qrcode");
    const generateBtn = document.getElementById("generateBtn");
    const downloadPdfLink = document.getElementById("downloadPdfLink");
    const qrStringOutput = document.getElementById("qrStringOutput");
    const infoButton = document.getElementById("infoButton");

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
    const MODULO_WEIGHTS_PREFIX = [10, 5, 8, 4, 2, 1]; // For 6-digit prefix
    const MODULO_WEIGHTS_ACCOUNT = [6, 3, 7, 9, 10, 5, 8, 4, 2, 1]; // For 10-digit account

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

    function validateTextForAlert(text) {
        if (typeof text !== 'string') return true;
        const unsupportedChars = text.match(/[^\x00-\x7F]/g) || [];
        const unsupported = unsupportedChars.filter(char => !characterMap[char]);
        if (unsupported.length > 0) {
            alert(`Některé zadané znaky nejsou přímo podporovány v QR kódu a budou nahrazeny nebo odstraněny: ${unsupported.join(", ")}. Zkontrolujte prosím výsledek.`);
        }
        return true;
    }
    
    function triggerQRCodeAnimation(animationClass) {
        qrCodeContainer.classList.remove('qr-code-enter', 'qr-code-update');
        void qrCodeContainer.offsetWidth; 
        if (animationClass) {
            qrCodeContainer.classList.add(animationClass);
        }
    }

    function generateQRCode(text, animationType = 'update') {
        qrCodeContainer.innerHTML = ""; // Clear previous QR/placeholder

        if (text === initialQRText) {
            // Consistent placeholder handling using styles from CSS for #qrcode p
            const placeholder = document.createElement('p');
            // Styles for placeholder are primarily handled by CSS rule: #qrcode p
            // We just set the content here.
            placeholder.textContent = initialQRText.substring(initialQRText.indexOf(':') + 2).trim();
            qrCodeContainer.appendChild(placeholder);
            triggerQRCodeAnimation(null); // No specific animation for placeholder, or 'qr-code-update' for a gentle fade
        } else {
            // Calculate size based on the container's current clientWidth.
            // This allows CSS to control the responsive width of the #qrcode container.
            let qrCodeSize = qrCodeContainer.clientWidth;

            // Subtract padding if #qrcode has horizontal padding and clientWidth includes it
            // For simplicity, assuming clientWidth is the usable area for the canvas.
            // Or, ensure #qrcode CSS uses box-sizing: border-box.

            if (qrCodeContainer.clientWidth === 0 && qrCodeContainer.offsetWidth > 0) {
                // Fallback if clientWidth is 0 but offsetWidth is available (e.g. scrollbars)
                qrCodeSize = qrCodeContainer.offsetWidth;
            }
            
            // Reduce size slightly to account for potential borders or inner spacing not covered by clientWidth
            // This is a small safety margin.
            qrCodeSize = qrCodeSize > 20 ? qrCodeSize -10 : qrCodeSize;


            if (qrCodeSize <= 0) { // Further fallback if clientWidth is 0 (e.g., display: none or not yet rendered)
                 qrCodeSize = (window.innerWidth < 767) ? 180 : 250; // Sensible default minimums
            }
            
            // Ensure a minimum reasonable size, but also don't exceed a max if necessary.
            // CSS max-width on #qrcode container should ideally handle the upper limit.
            qrCodeSize = Math.max(150, qrCodeSize); // Min size of 150px, adjust as needed
            qrCodeSize = Math.min(qrCodeSize, 370); // Max size cap if not handled by CSS alone.


            if (animationType === 'enter') triggerQRCodeAnimation('qr-code-enter');
            else if (animationType === 'update') triggerQRCodeAnimation('qr-code-update');
            else triggerQRCodeAnimation(null);

            new QRCode(qrCodeContainer, {
                text: text,
                width: qrCodeSize,
                height: qrCodeSize,
                colorDark: "#000000",
                colorLight: "#FFFFFF",
                correctLevel: QRCode.CorrectLevel.M,
            });
        }
        qrStringOutput.textContent = text; // Update the raw string output regardless
    }

    // --- New Validation Functions ---
    function isValidNumberString(value) {
        return /^\d+$/.test(value);
    }

    function validateCzechModulo11(numberStr, weights, fieldNameInCzech) {
        if (!isValidNumberString(numberStr)) {
            // This check might be redundant if called after direct numeric checks, but good for a standalone function
            return `Pole '${fieldNameInCzech}' smí obsahovat pouze číslice.`;
        }
        // Pad with leading zeros to match the length of the weights array
        const paddedNumberStr = numberStr.padStart(weights.length, '0');
        
        let sum = 0;
        for (let i = 0; i < paddedNumberStr.length; i++) {
            sum += parseInt(paddedNumberStr[i], 10) * weights[i];
        }
        if (sum % 11 !== 0) {
            return `Zadané ${fieldNameInCzech.toLowerCase()} neprošlo kontrolou platnosti (Modulo 11). Zkontrolujte prosím správnost čísla.`;
        }
        return null; // No error
    }
    // --- End of New Validation Functions ---

    function calculateIBAN(bankCode, prefix, accountNumber, silent = false, errorMessages = []) {
        const paddedPrefix = (prefix || '').padStart(6, '0');
        const paddedAccountNumber = (accountNumber || '').padStart(10, '0'); 

        const bban = `${bankCode}${paddedPrefix}${paddedAccountNumber}`;
        const numericIBAN = `${bban}123500`; // CZ = 1235

        try {
            // Basic check for non-numeric parts already in numericIBAN string, though BigInt would fail.
            if (!/^\d+$/.test(numericIBAN)) {
                 if (!silent) errorMessages.push("Chyba ve formátu čísla účtu pro výpočet IBANu (nesmí obsahovat nečíselné znaky).");
                 return null;
            }
            const checksumBigInt = 98n - (BigInt(numericIBAN) % 97n);
            let checkDigits = checksumBigInt.toString();
            if (checkDigits.length < 2) {
                checkDigits = '0' + checkDigits;
            }
            return `CZ${checkDigits}${bban}`;
        } catch (error) {
            if (!silent) {
                console.error("Error calculating IBAN checksum:", error, {bankCode, prefix, accountNumber, numericIBAN});
                errorMessages.push("Nepodařilo se vypočítat IBAN kontrolní součet. Ujistěte se, že všechny části čísla účtu obsahují pouze číslice.");
            }
            return null;
        }
    }

    function generateQRStringForUpdate(data, silentValidation = false) {
        let errorMessages = [];

        // 1. Validate Prefix
        if (data.prefix) { 
            if (!isValidNumberString(data.prefix)) {
                errorMessages.push("Předčíslí účtu smí obsahovat pouze číslice.");
            } else if (data.prefix.length > 6) {
                errorMessages.push("Předčíslí účtu může mít maximálně 6 číslic.");
            } else {
                const prefixError = validateCzechModulo11(data.prefix, MODULO_WEIGHTS_PREFIX, "Předčíslí účtu");
                if (prefixError) errorMessages.push(prefixError);
            }
        }

        // 2. Validate Account Number (mandatory for payment QR)
        if (!data.accountNumber) {
            errorMessages.push("Číslo účtu je povinný údaj."); 
        } else if (!isValidNumberString(data.accountNumber)) {
            errorMessages.push("Číslo účtu smí obsahovat pouze číslice.");
        } else if (data.accountNumber.length > 10) {
            errorMessages.push("Číslo účtu může mít maximálně 10 číslic.");
        } else if (data.accountNumber.length < 2 && !silentValidation) { 
             errorMessages.push("Číslo účtu musí mít alespoň 2 číslice.");
        }
         else {
            const accountToValidate = data.accountNumber.padStart(10, '0');
            const accountError = validateCzechModulo11(accountToValidate, MODULO_WEIGHTS_ACCOUNT, "Číslo účtu");
            if (accountError) errorMessages.push(accountError);
        }
        
        // 3. Validate Bank Code (mandatory)
        if (!data.bankCode) {
             errorMessages.push("Kód banky je povinný údaj."); 
        }


        if (errorMessages.length > 0 && !silentValidation) {
            alert(errorMessages.join("\n"));
            return initialQRText;
        }
        
        if (errorMessages.length > 0 && silentValidation && 
            (!data.accountNumber || !data.bankCode || !isValidNumberString(data.accountNumber) || (data.prefix && !isValidNumberString(data.prefix)))) {
            return initialQRText;
        }
        if (errorMessages.some(e => e.includes("Modulo 11")) && silentValidation && !errorMessages.some(e => e.includes("povinný údaj"))) {
            // If only Modulo11 failed silently, but mandatory fields are present, still show initialQRText
            // to indicate data isn't fully "clean" for a valid QR string yet.
             return initialQRText;
        }


        const iban = calculateIBAN(data.bankCode, data.prefix, data.accountNumber, silentValidation, errorMessages);
        if (!iban) {
            if (!silentValidation && errorMessages.length > 0 && !alertShownForErrors(errorMessages, ["Předčíslí účtu smí obsahovat pouze číslice.", "Číslo účtu smí obsahovat pouze číslice."])) { 
                // Avoid double alert if IBAN failed due to already alerted issues.
                // alert(errorMessages.join("\n")); // This might be too noisy if calculateIBAN adds a generic message.
            }
            return initialQRText;
        }
        
        // Helper to prevent re-alerting for the same fundamental errors
        function alertShownForErrors(currentErrors, alreadyAlertedSubstrings) {
            return alreadyAlertedSubstrings.some(sub => currentErrors.some(err => err.includes(sub)));
        }


        let amountStr = ""; // Default to empty string if no amount
        if (data.amount && data.amount.trim() !== "") {
            const amountNum = parseFloat(data.amount.replace(',', '.'));
            if (!isNaN(amountNum)) {
                amountStr = amountNum.toFixed(2);
                if (amountNum < 0 || amountStr.length > 10 || amountNum > 9999999.99) {
                    const msg = "Částka je neplatná, záporná, nebo příliš vysoká (max 9 999 999.99 Kč).";
                    if (!silentValidation) alert(msg); else errorMessages.push(msg); 
                    return initialQRText;
                }
            } else {
                const msg = "Zadaná částka není platné číslo.";
                if (!silentValidation) alert(msg); else errorMessages.push(msg);
                return initialQRText;
            }
        }

        let qrString = `SPD*1.0*ACC:${iban}`;
        if (amountStr) qrString += `*AM:${amountStr}`; // Only add AM if amount is present
        qrString += `*CC:CZK`; // Currency Code is mandatory

        if (data.receiverName) qrString += `*RN:${replaceUnsupportedCharacters(data.receiverName)}`;
        if (data.variableSymbol) qrString += `*X-VS:${data.variableSymbol}`;
        if (data.constantSymbol) qrString += `*X-KS:${data.constantSymbol}`;
        if (data.specificSymbol) qrString += `*X-SS:${data.specificSymbol}`;
        if (data.message) qrString += `*MSG:${replaceUnsupportedCharacters(data.message)}`;
        // PT:IP (Payment Type: Instant Payment) seems like a reasonable default.
        // Or it could be omitted if not strictly required by all banks for basic QR.
        // For now, keeping it as per original.
        qrString += `*PT:IP`;


        if (qrString.length > 330) { // Standard SPD length can vary, 330-350 is a common practical limit.
            const msg = "Vyplněné údaje jsou příliš dlouhé pro QR kód. Zkuste zkrátit zprávu nebo název příjemce.";
            if (!silentValidation) alert(msg); else errorMessages.push(msg);
            return initialQRText;
        }
        
        if (silentValidation && errorMessages.length > 0 && !errorMessages.some(e => e.includes("povinný údaj"))) {
             return initialQRText;
        }

        return qrString;
    }

    let debounceTimer;
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

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
        const qrString = generateQRStringForUpdate(currentData, true); 
        generateQRCode(qrString, 'update');
    }

    const debouncedLiveUpdate = debounce(handleLiveInputChange, 450);

    for (const key in allInputs) {
        if (allInputs.hasOwnProperty(key)) {
            const inputElement = allInputs[key];
            const eventType = (inputElement.tagName === 'SELECT') ? 'change' : 'input';
            inputElement.addEventListener(eventType, debouncedLiveUpdate);
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
            qrCodeContainer.innerHTML = '<p style="color:red; text-align:center; padding: 20px;">Chyba: Nepodařilo se načíst kódy bank. Funkčnost omezena.</p>';
        })
        .finally(() => {
            generateQRCode(initialQRText, 'enter'); // Generate initial placeholder
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
            generateQRCode(initialQRText, 'enter'); 
            return;
        }
        
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

        const qrString = generateQRStringForUpdate(currentData, false); 
        
        generateQRCode(qrString, 'enter'); 

        if (qrString && qrString !== initialQRText && window.innerWidth < 767) {
             // Ensure qrCodeContainer is visible before scrolling to it.
             // If it's inside a display:none parent, scrollIntoView might not work as expected.
             // Assuming it's visible.
             setTimeout(() => { // Add a slight delay to ensure rendering before scroll
                qrCodeContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
             }, 100);
        }
    });

    infoButton.addEventListener("click", () => {
        qrStringOutput.style.display = (qrStringOutput.style.display === "none" || qrStringOutput.style.display === "") ? "block" : "none";
    });

    allInputs.accountNumber.addEventListener('paste', function (event) {
        event.preventDefault();
        const paste = (event.clipboardData || window.clipboardData).getData('text');
        parseAccountNumber(paste); 
        debouncedLiveUpdate(); 
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
            alert('Formát čísla účtu pro vložení není platný. Použijte např. 123456-1234567890/0100, číslo účtu/kód banky, nebo jen číslo účtu.');
        }
    }

    downloadPdfLink.addEventListener("click", function (event) {
        event.preventDefault();

        if (qrStringOutput.textContent === initialQRText || qrStringOutput.textContent.startsWith("INFO:") || !qrCodeContainer.querySelector("canvas")) {
            alert("Nejprve prosím vygenerujte platný platební QR kód vyplněním údajů.");
            return;
        }
        const qrCanvas = qrCodeContainer.querySelector("canvas");
        if (!qrCanvas) { 
            alert("QR kód není k dispozici pro stažení.");
            return;
        }

        const qrDataUrl = qrCanvas.toDataURL("image/png");
        
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
            if (receiver) {
                fileName = `${receiver}_${amountVal !== "0.00" ? amountVal.replace('.',',') : 'platba'}_qr.pdf`;
            } else if (amountVal !== "0.00") {
                 fileName = `platba_${amountVal.replace('.',',')}_qr.pdf`;
            }
            pdfMake.createPdf(docDefinition).download(fileName);
        } catch(e) {
            console.error("Error creating PDF: ", e);
            alert("Nepodařilo se vytvořit PDF. Zkontrolujte konzoli pro detaily.");
        }
    });
});
