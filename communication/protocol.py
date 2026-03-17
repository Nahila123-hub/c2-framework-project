"""
C2 Communication Protocol Layer
Wraps all messages in a structured JSON envelope with:
  - msg_type  (register, heartbeat, command, output, etc.)
  - timestamp (epoch seconds)
  - payload   (the actual data, encrypted)
  - signature (HMAC of the ciphertext for integrity)
"""

import json
import time
import sys
import os

# Add project root to path so we can import the encryption module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from encryption.crypto import encrypt_message, decrypt_message, sign_message, verify_signature


# ── Build / Parse Protocol Messages ──────────────────────────────

def build_message(msg_type: str, payload: dict) -> str:
    """
    Builds an encrypted protocol message.
    1. Serializes payload to JSON
    2. Encrypts the JSON bytes
    3. Signs the ciphertext
    4. Returns a JSON string envelope
    """
    raw = json.dumps(payload).encode()
    ciphertext = encrypt_message(raw)
    signature = sign_message(ciphertext.encode())

    envelope = {
        "msg_type": msg_type,
        "timestamp": int(time.time()),
        "ciphertext": ciphertext,
        "signature": signature
    }

    return json.dumps(envelope)


def parse_message(raw_message: str) -> dict:
    """
    Parses and decrypts a protocol message.
    1. Deserializes the JSON envelope
    2. Verifies the HMAC signature
    3. Decrypts the ciphertext
    4. Returns dict with msg_type, timestamp, and decrypted payload
    Raises ValueError on invalid/tampered messages.
    """
    envelope = json.loads(raw_message)

    required_keys = {"msg_type", "timestamp", "ciphertext", "signature"}
    if not required_keys.issubset(envelope.keys()):
        raise ValueError(f"Invalid message — missing keys: {required_keys - envelope.keys()}")

    # Verify integrity
    if not verify_signature(envelope["ciphertext"].encode(), envelope["signature"]):
        raise ValueError("Signature verification failed — message tampered!")

    # Decrypt payload
    plaintext = decrypt_message(envelope["ciphertext"])
    payload = json.loads(plaintext.decode())

    return {
        "msg_type": envelope["msg_type"],
        "timestamp": envelope["timestamp"],
        "payload": payload
    }


# ── Convenience Helpers ──────────────────────────────────────────

def encrypt_payload(payload: dict) -> dict:
    """
    Encrypts a payload dict and returns {ciphertext, signature}.
    Used when sending data to the server via existing HTTP endpoints.
    """
    raw = json.dumps(payload).encode()
    ciphertext = encrypt_message(raw)
    signature = sign_message(ciphertext.encode())
    return {
        "ciphertext": ciphertext,
        "signature": signature
    }


def decrypt_payload(data: dict) -> dict:
    """
    Decrypts a {ciphertext, signature} dict back to the original payload.
    Raises ValueError if signature is invalid.
    """
    if not verify_signature(data["ciphertext"].encode(), data["signature"]):
        raise ValueError("Signature verification failed!")

    plaintext = decrypt_message(data["ciphertext"])
    return json.loads(plaintext.decode())
