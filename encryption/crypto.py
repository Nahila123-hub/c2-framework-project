import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SECRET_KEY = b'0123456789abcdef'


def encrypt_message(message: bytes):

    aes = AESGCM(SECRET_KEY)

    nonce = os.urandom(12)

    ciphertext = aes.encrypt(nonce, message, None)

    encrypted = nonce + ciphertext

    return base64.b64encode(encrypted).decode()


def decrypt_message(encoded_ciphertext: str):

    aes = AESGCM(SECRET_KEY)

    encrypted = base64.b64decode(encoded_ciphertext)

    nonce = encrypted[:12]

    ciphertext = encrypted[12:]

    plaintext = aes.decrypt(nonce, ciphertext, None)

    return plaintext