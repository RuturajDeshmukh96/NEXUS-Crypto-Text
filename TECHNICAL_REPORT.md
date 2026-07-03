# Technical Report: NEXUS CryptoText
**Application:** CryptoText (NEXUS)
**Type:** Secure web app for encrypted text handling and AI-assisted analysis

---

## 1. Summary
NEXUS is a Django-based web application that lets authorized users encrypt and decrypt text securely. It also records every action, monitors user sessions, and analyzes decrypted content for sentiment and threats using Google Gemini when available.

The app is built to be simple, secure, and recover gracefully if the AI service is unavailable.

---

## 2. What It Does
1. User login and profile management
2. Text encryption with a secret key or generated key
3. Text decryption with the same secret key
4. Operation history logging
5. Optional AI analysis after decryption
6. Session and device tracking for security

---

## 3. Key Technologies
* Python 3.11/3.12
* Django 5.x
* SQLite (`db.sqlite3`)
* `cryptography` for secure encryption
* Google Gemini API (`google-generativeai`) for optional AI analysis
* HTML/CSS/JavaScript for frontend

---

## 4. Encryption Method
* Uses Fernet symmetric encryption from `cryptography`.
* User key or generated random key is converted into a 32-byte Fernet key using SHA-256.
* The app can generate a secure random key if the user does not provide one.
* Encrypted output is stored and shown as Base64 text.

---

## 5. Decryption and AI Analysis
* Decryption requires the same secret key used for encryption.
* If decryption succeeds, the app may call Google Gemini to analyze the plaintext.
* The AI analysis returns sentiment, language, threat assessment, summary, and word count.
* If Google Gemini is unavailable, the app falls back to a simple local analysis mode.

---

## 6. Data Tracking
The application records security-related information in the database:
* `UserProfile` extends user data with phone number and profile details.
* `CryptoLog` stores encryption/decryption events, status, and a text preview.
* `UserDeviceSession` stores login device info such as IP address and browser agent.
* `DecryptionVerification` stores one-time verification tokens for extra checks.

---

## 7. Main Workflow
### Encryption
1. User enters plaintext and optional key.
2. If no key is given, the system generates one.
3. The key is hashed and converted for Fernet.
4. Text is encrypted and logged.

### Decryption
1. User enters ciphertext and key.
2. The key is used to decrypt the text.
3. Success or failure is logged.
4. On success, AI analysis is performed if available.

---

## 8. Project Structure
* `manage.py` – Django command tool
* `config/` – settings, URLs, ASGI/WSGI setup
* `core/` – encryption logic, models, views, forms, routes
* `templates/` – HTML pages for login, dashboard, encrypt/decrypt, history
* `static/` – CSS and JavaScript files
* `requirements.txt` – Python dependencies

---

## 9. Important Notes
* The system is designed for development and testing, not production deployment.
* Google Gemini is optional; the app still works without it.
* The app stores encrypted data and logs operations for accountability.
* The project can run locally with `py -3 manage.py runserver`.
