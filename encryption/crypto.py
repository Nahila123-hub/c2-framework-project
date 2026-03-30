"""
C2 Encryption Module
- AES-256-GCM encryption/decryption
- HMAC-SHA256 message signing/verification
- PBKDF2 key derivation
- Keys loaded from environment variables with secure fallbacks
"""

import os
import base64
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ── Key Management ──────────────────────────────────────────────
# Keys are loaded from environment variables for security.
# Fallback defaults are provided for development ONLY.

def _load_key(env_var: str, default: bytes, expected_len: int) -> bytes:
    """Load a key from an environment variable, or use the default."""
    raw = os.environ.get(env_var, "")
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
        # Pad or truncate to expected length
        if len(key) < expected_len:
            key = key.ljust(expected_len, b'\x00')
        return key[:expected_len]
    return default


# AES-256 requires a 32-byte (256-bit) key
SECRET_KEY = _load_key(
    "C2_AES_KEY",
    b'0123456789abcdef0123456789abcdef',  # 32 bytes for AES-256
    32
)

# HMAC signing key
HMAC_KEY = _load_key(
    "C2_HMAC_KEY",
    b'c2-hmac-signing-key-2024-secure!',  # 32 bytes
    32
)

# API authentication key for server endpoints
API_KEY = os.environ.get("C2_API_KEY", "c2-default-api-key-change-me")


# ── Key Derivation ──────────────────────────────────────────────

def derive_key(password: str, salt: bytes = None) -> tuple:
    """
    Derives a 256-bit AES key from a password using PBKDF2-HMAC-SHA256.
    Returns (derived_key, salt) — store the salt alongside the key.
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,          # 32 bytes = 256-bit key for AES-256
        salt=salt,
        iterations=100_000,
    )
    key = kdf.derive(password.encode())
    return key, salt


# ── AES-256-GCM Encryption / Decryption ─────────────────────────

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
    Decrypts a base64-encoded AES-256-GCM ciphertext.
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