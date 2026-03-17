import os
import base64
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Default shared secret — used for both AES encryption and HMAC signing
SECRET_KEY = b'0123456789abcdef'
HMAC_KEY = b'c2-hmac-signing-key-2024'


# ── Key Derivation ──────────────────────────────────────────────

def derive_key(password: str, salt: bytes = None) -> tuple:
    """
    Derives a 128-bit AES key from a password using PBKDF2-HMAC-SHA256.
    Returns (derived_key, salt) — store the salt alongside the key.
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        iterations=100_000,
    )
    key = kdf.derive(password.encode())
    return key, salt


# ── AES-GCM Encryption / Decryption ─────────────────────────────

def encrypt_message(message: bytes, key: bytes = None) -> str:
    """
    Encrypts a message with AES-256-GCM.
    Returns base64-encoded string of (nonce + ciphertext).
    """
    if key is None:
        key = SECRET_KEY

    aes = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aes.encrypt(nonce, message, None)
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode()


def decrypt_message(encoded_ciphertext: str, key: bytes = None) -> bytes:
    """
    Decrypts a base64-encoded AES-GCM ciphertext.
    Returns the original plaintext bytes.
    """
    if key is None:
        key = SECRET_KEY

    aes = AESGCM(key)
    encrypted = base64.b64decode(encoded_ciphertext)
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    plaintext = aes.decrypt(nonce, ciphertext, None)
    return plaintext


# ── HMAC Message Signing ─────────────────────────────────────────

def sign_message(data: bytes, key: bytes = None) -> str:
    """
    Creates an HMAC-SHA256 signature of the data.
    Returns hex-encoded signature string.
    """
    if key is None:
        key = HMAC_KEY

    signature = hmac.new(key, data, hashlib.sha256).hexdigest()
    return signature


def verify_signature(data: bytes, signature: str, key: bytes = None) -> bool:
    """
    Verifies an HMAC-SHA256 signature.
    Returns True if the signature matches.
    """
    if key is None:
        key = HMAC_KEY

    expected = hmac.new(key, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Convenience: Encrypt + Sign / Decrypt + Verify ───────────────

def secure_encrypt(message: bytes) -> dict:
    """
    Encrypts a message AND signs the ciphertext.
    Returns dict with 'ciphertext' and 'signature'.
    """
    ciphertext = encrypt_message(message)
    signature = sign_message(ciphertext.encode())
    return {
        "ciphertext": ciphertext,
        "signature": signature
    }


def secure_decrypt(ciphertext: str, signature: str) -> bytes:
    """
    Verifies signature, then decrypts. Raises ValueError on bad signature.
    """
    if not verify_signature(ciphertext.encode(), signature):
        raise ValueError("Signature verification failed — message tampered!")

    return decrypt_message(ciphertext)