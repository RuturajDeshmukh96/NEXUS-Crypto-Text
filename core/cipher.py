import base64
import hashlib
import secrets
import string
from cryptography.fernet import Fernet, InvalidToken

def get_fernet_key(passphrase: str) -> bytes:
    """Generate a consistent 32-byte URL-safe base64 key from any passphrase string using SHA-256."""
    digest = hashlib.sha256(passphrase.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)

def generate_random_passphrase(length=16) -> str:
    """Generate a secure random passphrase if one is not provided."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def encrypt_text(raw_text: str, passphrase: str) -> str:
    """Encrypts plaintext using AES-128 via Fernet."""
    key = get_fernet_key(passphrase)
    f = Fernet(key)
    return f.encrypt(raw_text.encode('utf-8')).decode('utf-8')

def decrypt_text(cipher_text: str, passphrase: str) -> str:
    """Decrypts cipher text using AES-128 via Fernet. Returns None if invalid."""
    key = get_fernet_key(passphrase)
    f = Fernet(key)
    try:
        return f.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        return None
