"""
Unit Tests for C2 Framework
Tests cover:
  - crypto.py: encrypt/decrypt, sign/verify, key derivation, secure_encrypt/decrypt
  - protocol.py: build/parse messages, anti-replay, payload encrypt/decrypt
  - agent.py: command routing for built-in commands
  - server_async.py: API endpoint tests via FastAPI TestClient
"""

import sys
import os
import json
import time
import unittest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ════════════════════════════════════════════════════════════════
# Crypto Tests
# ════════════════════════════════════════════════════════════════

class TestCrypto(unittest.TestCase):
    """Tests for encryption/crypto.py"""

    def test_encrypt_decrypt_roundtrip(self):
        from encryption.crypto import encrypt_message, decrypt_message
        original = b"Hello, C2 Framework!"
        encrypted = encrypt_message(original)
        decrypted = decrypt_message(encrypted)
        self.assertEqual(original, decrypted)

    def test_encrypt_produces_different_ciphertexts(self):
        from encryption.crypto import encrypt_message
        msg = b"Same message"
        enc1 = encrypt_message(msg)
        enc2 = encrypt_message(msg)
        # Random nonce ensures different ciphertexts each time
        self.assertNotEqual(enc1, enc2)

    def test_sign_verify_roundtrip(self):
        from encryption.crypto import sign_message, verify_signature
        data = b"Important data to sign"
        signature = sign_message(data)
        self.assertTrue(verify_signature(data, signature))

    def test_verify_rejects_tampered_data(self):
        from encryption.crypto import sign_message, verify_signature
        data = b"Original data"
        signature = sign_message(data)
        # Tamper with data
        self.assertFalse(verify_signature(b"Tampered data", signature))

    def test_verify_rejects_wrong_signature(self):
        from encryption.crypto import verify_signature
        data = b"Some data"
        self.assertFalse(verify_signature(data, "0" * 64))

    def test_secure_encrypt_decrypt(self):
        from encryption.crypto import secure_encrypt, secure_decrypt
        original = b"Secure message test"
        result = secure_encrypt(original)
        self.assertIn("ciphertext", result)
        self.assertIn("signature", result)
        decrypted = secure_decrypt(result["ciphertext"], result["signature"])
        self.assertEqual(original, decrypted)

    def test_secure_decrypt_rejects_tampered(self):
        from encryption.crypto import secure_encrypt, secure_decrypt
        result = secure_encrypt(b"test")
        with self.assertRaises(ValueError):
            secure_decrypt(result["ciphertext"] + "x", result["signature"])

    def test_derive_key(self):
        from encryption.crypto import derive_key
        key1, salt1 = derive_key("password123")
        key2, salt2 = derive_key("password123", salt1)
        # Same password + same salt = same key
        self.assertEqual(key1, key2)
        # Key must be 32 bytes (256-bit)
        self.assertEqual(len(key1), 32)

    def test_derive_key_different_passwords(self):
        from encryption.crypto import derive_key
        key1, salt = derive_key("password1")
        key2, _ = derive_key("password2", salt)
        self.assertNotEqual(key1, key2)

    def test_encrypt_empty_message(self):
        from encryption.crypto import encrypt_message, decrypt_message
        encrypted = encrypt_message(b"")
        decrypted = decrypt_message(encrypted)
        self.assertEqual(b"", decrypted)

    def test_encrypt_large_message(self):
        from encryption.crypto import encrypt_message, decrypt_message
        original = b"A" * 10000
        encrypted = encrypt_message(original)
        decrypted = decrypt_message(encrypted)
        self.assertEqual(original, decrypted)


# ════════════════════════════════════════════════════════════════
# Protocol Tests
# ════════════════════════════════════════════════════════════════

class TestProtocol(unittest.TestCase):
    """Tests for communication/protocol.py"""

    def test_build_parse_roundtrip(self):
        from communication.protocol import build_message, parse_message
        payload = {"agent_id": "test-123", "command": "sysinfo"}
        raw = build_message("command", payload)
        parsed = parse_message(raw)
        self.assertEqual(parsed["msg_type"], "command")
        self.assertEqual(parsed["payload"], payload)

    def test_parse_detects_tampered_message(self):
        from communication.protocol import build_message, parse_message
        raw = build_message("test", {"key": "value"})
        # Tamper with the message
        envelope = json.loads(raw)
        envelope["ciphertext"] = envelope["ciphertext"][:-1] + "X"
        with self.assertRaises(ValueError):
            parse_message(json.dumps(envelope))

    def test_parse_rejects_missing_keys(self):
        from communication.protocol import parse_message
        with self.assertRaises(ValueError):
            parse_message(json.dumps({"msg_type": "test"}))

    def test_anti_replay_rejects_old_messages(self):
        from communication.protocol import parse_message
        from encryption.crypto import encrypt_message, sign_message
        # Build a message with very old timestamp
        payload = json.dumps({"test": "data"}).encode()
        ciphertext = encrypt_message(payload)
        signature = sign_message(ciphertext.encode())
        envelope = {
            "msg_type": "test",
            "timestamp": int(time.time()) - 600,  # 10 minutes ago
            "ciphertext": ciphertext,
            "signature": signature
        }
        with self.assertRaises(ValueError):
            parse_message(json.dumps(envelope))

    def test_encrypt_decrypt_payload(self):
        from communication.protocol import encrypt_payload, decrypt_payload
        original = {"agent_id": "abc-123", "data": "secret"}
        encrypted = encrypt_payload(original)
        decrypted = decrypt_payload(encrypted)
        self.assertEqual(original, decrypted)

    def test_protocol_version_included(self):
        from communication.protocol import build_message, parse_message
        raw = build_message("test", {"key": "val"})
        parsed = parse_message(raw)
        self.assertIn("version", parsed)


# ════════════════════════════════════════════════════════════════
# Agent Command Router Tests
# ════════════════════════════════════════════════════════════════

class TestAgentCommands(unittest.TestCase):
    """Tests for agent/agent.py command handlers"""

    def test_sysinfo(self):
        from agent.agent import handle_sysinfo
        result = handle_sysinfo()
        self.assertIn("hostname:", result)
        self.assertIn("username:", result)
        self.assertIn("os_name:", result)

    def test_whoami(self):
        from agent.agent import handle_whoami
        result = handle_whoami()
        self.assertIn("@", result)

    def test_pwd(self):
        from agent.agent import handle_pwd
        result = handle_pwd()
        self.assertTrue(os.path.isabs(result))

    def test_ls_current_dir(self):
        from agent.agent import handle_ls
        result = handle_ls(".")
        # Should show at least something
        self.assertTrue(len(result) > 0)

    def test_ls_nonexistent(self):
        from agent.agent import handle_ls
        result = handle_ls("/nonexistent_dir_12345")
        self.assertIn("Error", result)

    def test_cd_and_back(self):
        from agent.agent import handle_cd
        original = os.getcwd()
        try:
            result = handle_cd(os.path.dirname(original))
            self.assertIn("Changed directory", result)
        finally:
            os.chdir(original)

    def test_cd_invalid(self):
        from agent.agent import handle_cd
        result = handle_cd("/nonexistent_12345")
        self.assertIn("Error", result)

    def test_diskinfo(self):
        from agent.agent import handle_diskinfo
        result = handle_diskinfo()
        self.assertIn("Disk Usage", result)

    def test_execute_command_help(self):
        from agent.agent import execute_command
        result = execute_command("help", "http://localhost:8000", "test-id")
        self.assertIn("Available commands", result)
        self.assertIn("sysinfo", result)

    def test_execute_command_routes_correctly(self):
        from agent.agent import execute_command
        result = execute_command("whoami", "http://localhost:8000", "test-id")
        self.assertIn("@", result)

    def test_execute_shell(self):
        from agent.agent import execute_shell
        if os.name == 'nt':
            result = execute_shell("echo hello")
        else:
            result = execute_shell("echo hello")
        self.assertIn("hello", result)


# ════════════════════════════════════════════════════════════════
# Server API Tests (using FastAPI TestClient)
# ════════════════════════════════════════════════════════════════

class TestServerAPI(unittest.TestCase):
    """Tests for server/server_async.py API endpoints"""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from server.server_async import app
            from encryption.crypto import API_KEY
            cls.client = TestClient(app)
            cls.api_key = API_KEY
            cls.has_deps = True
        except ImportError:
            cls.has_deps = False

    def setUp(self):
        if not self.has_deps:
            self.skipTest("FastAPI/TestClient not installed")

    def auth_headers(self):
        return {"X-API-Key": self.api_key}

    def test_home(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["version"], "3.0")

    def test_auth_login_valid(self):
        res = self.client.post("/auth/login", json={"api_key": self.api_key})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["authenticated"])

    def test_auth_login_invalid(self):
        res = self.client.post("/auth/login", json={"api_key": "wrong-key"})
        self.assertEqual(res.status_code, 401)

    def test_register_agent(self):
        agent = {
            "agent_id": "test-unit-001",
            "hostname": "testhost",
            "username": "testuser",
            "os_name": "TestOS",
            "ip_address": "127.0.0.1",
            "tags": "test,unit"
        }
        res = self.client.post("/register", json=agent)
        self.assertEqual(res.status_code, 200)

    def test_agents_requires_auth(self):
        res = self.client.get("/agents")
        self.assertEqual(res.status_code, 401)

    def test_agents_with_auth(self):
        res = self.client.get("/agents", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_send_command_requires_auth(self):
        res = self.client.post("/command", json={
            "agent_id": "test-unit-001",
            "command": "sysinfo"
        })
        self.assertEqual(res.status_code, 401)

    def test_send_command_with_priority(self):
        res = self.client.post("/command", json={
            "agent_id": "test-unit-001",
            "command": "sysinfo",
            "priority": 2
        }, headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_heartbeat(self):
        res = self.client.post("/heartbeat", json={"agent_id": "test-unit-001"})
        self.assertEqual(res.status_code, 200)

    def test_dashboard_requires_auth(self):
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 401)

    def test_dashboard_with_auth(self):
        res = self.client.get("/dashboard", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_agents", data)
        self.assertIn("online_agents", data)

    def test_logs_with_auth(self):
        res = self.client.get("/logs", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_logs_export_json(self):
        res = self.client.get("/logs/export?format=json", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_logs_export_csv(self):
        res = self.client.get("/logs/export?format=csv", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)
        self.assertIn("csv", res.json())

    def test_send_and_get_output(self):
        # Send output
        res = self.client.post("/send_output", json={
            "agent_id": "test-unit-001",
            "command": "whoami",
            "output": "testuser@testhost"
        })
        self.assertEqual(res.status_code, 200)

        # Get outputs
        res = self.client.get("/outputs", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) > 0)

    def test_tag_update(self):
        # First register the agent
        self.client.post("/register", json={
            "agent_id": "test-unit-001",
            "hostname": "testhost",
            "username": "testuser",
            "os_name": "TestOS",
        })
        res = self.client.post("/agent/tags", json={
            "agent_id": "test-unit-001",
            "tags": "windows,finance,hq"
        }, headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_delete_agent(self):
        # Register then delete
        self.client.post("/register", json={
            "agent_id": "test-delete-001",
            "hostname": "delhost",
            "username": "deluser",
            "os_name": "DelOS",
        })
        res = self.client.delete("/agent/test-delete-001", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_history(self):
        res = self.client.get("/history", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_history_by_agent(self):
        res = self.client.get("/history?agent_id=test-unit-001", headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)

    def test_broadcast(self):
        res = self.client.post("/broadcast", json={
            "command": "sysinfo",
            "priority": 1
        }, headers=self.auth_headers())
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
