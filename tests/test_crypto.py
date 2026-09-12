"""
Unit Tests for Cryptography Layer.
Validates TripleDES ECB PKCS7 (C# CryptHelper compatibility) and AES-256.
"""
import unittest
import os
import sys

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.crypto import (
    encrypt_des3,
    decrypt_des3,
    calc_md5_hash,
    verify_md5_hash,
    CryptoManager,
)


class TestCrypto(unittest.TestCase):

    def test_des3_roundtrip(self):
        key = "MyMasterSecretKey2026"
        plain_text = "DatabasePassword@#$12345"
        encrypted = encrypt_des3(key, plain_text)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, plain_text)

        decrypted = decrypt_des3(key, encrypted)
        self.assertEqual(decrypted, plain_text)

    def test_des3_empty_string(self):
        key = "SomeKey"
        self.assertEqual(encrypt_des3(key, ""), "")
        self.assertEqual(decrypt_des3(key, ""), "")

    def test_des3_wrong_key_fails(self):
        key = "CorrectKey123"
        wrong_key = "WrongKey456"
        plain_text = "TopSecretInfo"
        encrypted = encrypt_des3(key, plain_text)

        with self.assertRaises(ValueError):
            decrypt_des3(wrong_key, encrypted)

    def test_md5_hash(self):
        test_val = "admin123"
        # Known MD5 for 'admin123' is 0192023a7bbd73250516f069df18b500
        expected = "0192023a7bbd73250516f069df18b500"
        self.assertEqual(calc_md5_hash(test_val), expected)
        self.assertTrue(verify_md5_hash(test_val, expected))

    def test_aes256_roundtrip(self):
        key = os.urandom(32)
        message = "High Security Secret Payload"
        encrypted = CryptoManager.encrypt_aes256(key, message)
        decrypted = CryptoManager.decrypt_aes256(key, encrypted)
        self.assertEqual(decrypted, message)


if __name__ == "__main__":
    unittest.main()
