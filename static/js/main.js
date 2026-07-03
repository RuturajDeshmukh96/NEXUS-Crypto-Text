/* =========================================================================
   Crypto Text - Frontend UI Interactions
   ========================================================================= */

document.addEventListener('DOMContentLoaded', () => {

    /* --- Sidebar Toggle Logic --- */
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    /* --- Password Strength Meter Logic (Register Page) --- */
    const passwordInput = document.getElementById('register-password');
    const strengthBar = document.getElementById('strength-bar');
    const strengthLabel = document.getElementById('strength-label');

    if (passwordInput && strengthBar && strengthLabel) {
        passwordInput.addEventListener('input', (e) => {
            const val = e.target.value;
            let strength = 0;
            
            if (val.length >= 8) strength += 25;
            if (/[A-Z]/.test(val)) strength += 25;
            if (/[a-z]/.test(val)) strength += 25;
            if (/[0-9]/.test(val) || /[^A-Za-z0-9]/.test(val)) strength += 25;

            strengthBar.style.width = strength + '%';

            // Checklist Icons Logic
            const checklistItems = document.querySelectorAll('.strength-meter + .strength-text + div i');
            if (checklistItems.length === 4) {
                checklistItems[0].style.color = val.length >= 8 ? 'var(--success)' : 'var(--text-muted)';
                checklistItems[1].style.color = /[A-Z]/.test(val) ? 'var(--success)' : 'var(--text-muted)';
                checklistItems[2].style.color = /[0-9]/.test(val) ? 'var(--success)' : 'var(--text-muted)';
                checklistItems[3].style.color = /[^A-Za-z0-9]/.test(val) ? 'var(--success)' : 'var(--text-muted)';
            }

            if (val.length === 0) {
                strengthBar.style.width = '0%';
                strengthLabel.textContent = 'Enter password';
                strengthLabel.style.color = 'var(--text-muted)';
            } else if (strength <= 25) {
                strengthBar.style.backgroundColor = 'var(--danger)';
                strengthLabel.textContent = 'Weak';
                strengthLabel.style.color = 'var(--danger)';
            } else if (strength <= 75) {
                strengthBar.style.backgroundColor = 'var(--warning)';
                strengthLabel.textContent = 'Medium';
                strengthLabel.style.color = 'var(--warning)';
            } else {
                strengthBar.style.backgroundColor = 'var(--success)';
                strengthLabel.textContent = 'Strong';
                strengthLabel.style.color = 'var(--success)';
            }
        });
    }

    /* --- Password Generator Logic --- */
    const genLength = document.getElementById('gen-length');
    const genLengthVal = document.getElementById('gen-length-val');
    const genUpper = document.getElementById('gen-upper');
    const genLower = document.getElementById('gen-lower');
    const genNumbers = document.getElementById('gen-numbers');
    const genSymbols = document.getElementById('gen-symbols');
    const genBtn = document.getElementById('generate-btn');
    const genOutput = document.getElementById('gen-output');
    const genCopyBtn = document.getElementById('gen-copy-btn');

    if (genLength && genOutput) {
        genLength.addEventListener('input', (e) => {
            genLengthVal.textContent = e.target.value;
        });

        const generatePassword = () => {
            const len = parseInt(genLength.value);
            const upperChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            const lowerChars = 'abcdefghijklmnopqrstuvwxyz';
            const numberChars = '0123456789';
            const symbolChars = '!@#$%^&*()_+~`|}{[]:;?><,./-=';
            
            let allowedChars = '';
            if (genUpper.checked) allowedChars += upperChars;
            if (genLower.checked) allowedChars += lowerChars;
            if (genNumbers.checked) allowedChars += numberChars;
            if (genSymbols.checked) allowedChars += symbolChars;

            if (allowedChars.length === 0) {
                genOutput.value = 'Please select at least one character type.';
                return;
            }

            let newPassword = '';
            for (let i = 0; i < len; i++) {
                const randomIndex = Math.floor(Math.random() * allowedChars.length);
                newPassword += allowedChars[randomIndex];
            }
            genOutput.value = newPassword;
            
            // Auto trigger typing effect for cyber feel
            genOutput.style.opacity = '0.5';
            setTimeout(() => { genOutput.style.opacity = '1'; }, 150);
        };

        genBtn.addEventListener('click', generatePassword);
        generatePassword(); // Generate on load

        genCopyBtn.addEventListener('click', () => {
            if(!genOutput.value) return;
            navigator.clipboard.writeText(genOutput.value);
            const originalHTML = genCopyBtn.innerHTML;
            genCopyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
            genCopyBtn.classList.replace('btn-outline', 'btn-primary');
            setTimeout(() => {
                genCopyBtn.innerHTML = originalHTML;
                genCopyBtn.classList.replace('btn-primary', 'btn-outline');
            }, 2000);
        });
    }

    /* --- 2-Step Verification Modal (Decrypt Page) --- */
    const decryptBtn = document.getElementById('trigger-decrypt-btn');
    const twoStepModal = document.getElementById('two-step-modal');
    const verifyBtn = document.getElementById('verify-code-btn');
    const cancelBtn = document.getElementById('cancel-verify-btn');
    const decryptResult = document.getElementById('decrypt-result-area');

    if (decryptBtn && twoStepModal) {
        // Logic handled backend via view context override
        /* decryptBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent standard form submission for UI demo
            
            // Check if input is empty
            const cipherInput = document.getElementById('cipher-input').value;
            if(cipherInput.trim() === '') {
                alert('Please enter cipher text to decrypt.');
                return;
            }

            // Show Custom UI Modal
            twoStepModal.classList.add('active');
        }); */

        cancelBtn.addEventListener('click', () => {
            twoStepModal.classList.remove('active');
        });

        // OTP Input Auto-focus logic
        const otpInputs = document.querySelectorAll('.otp-input');
        otpInputs.forEach((input, index) => {
            input.addEventListener('keyup', (e) => {
                if(e.key >= 0 && e.key <= 9) {
                    if(index < otpInputs.length - 1) {
                        otpInputs[index + 1].focus();
                    }
                } else if (e.key === 'Backspace') {
                    if(index > 0) {
                        otpInputs[index - 1].focus();
                    }
                }
            });
        });

        verifyBtn.addEventListener('click', () => {
            // Simulate verification
            verifyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';
            
            setTimeout(() => {
                twoStepModal.classList.remove('active');
                verifyBtn.innerHTML = 'Verify & Decrypt';
                
                // Show result area and hide empty state
                document.getElementById('decrypt-empty-state').style.display = 'none';
                decryptResult.style.display = 'block';
                decryptResult.classList.add('fade-in');
                
                // Reset OTP fields
                otpInputs.forEach(input => input.value = '');

            }, 1500);
        });
    }

    /* --- General Copy Handlers --- */
    const copyBtns = document.querySelectorAll('.copy-trigger');
    copyBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-clipboard-target');
            const targetEl = document.querySelector(targetId);
            if(targetEl) {
                let textToCopy = targetEl.tagName === 'INPUT' || targetEl.tagName === 'TEXTAREA' ? targetEl.value : targetEl.innerText;
                navigator.clipboard.writeText(textToCopy);
                
                const originalHtml = this.innerHTML;
                this.innerHTML = '<i class="fa-solid fa-check"></i>';
                setTimeout(() => {
                    this.innerHTML = originalHtml;
                }, 2000);
            }
        });
    });

});
