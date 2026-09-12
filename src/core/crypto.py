"""
Cryptography Module for DigitalBrainEX AI.
Provides 100% binary-compatible decryption and encryption matching C# CryptHelper
(TripleDES ECB PKCS7 with MD5 key derivation), plus modern AES-256-GCM cipher support.
"""
import base64
import hashlib
import os
from typing import Optional
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_des3_key(key: str) -> bytes:
    """
    Derives a 16-byte DES3 key by computing the MD5 hash of the UTF-8 key string.
    Matches C#:
      byte[] securityKeyArray = objMD5CryptoService.ComputeHash(UTF8Encoding.UTF8.GetBytes(key));
    """
    return hashlib.md5(key.encode("utf-8")).digest()


def encrypt_des3(key: str, plain_text: str) -> str:
    """
    Encrypts plain_text using TripleDES ECB PKCS7, compatible with C# CryptHelper.EncryptString.
    Returns Base64-encoded ciphertext string.
    """
    if not plain_text:
        return ""
    key_bytes = _derive_des3_key(key)
    cipher = DES3.new(key_bytes, DES3.MODE_ECB)
    raw_data = plain_text.encode("utf-8")
    padded_data = pad(raw_data, DES3.block_size, style="pkcs7")
    encrypted_bytes = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted_bytes).decode("utf-8")


def decrypt_des3(key: str, cipher_b64: str) -> str:
    """
    Decrypts cipher_b64 using TripleDES ECB PKCS7, compatible with C# CryptHelper.DecryptString.
    Returns decrypted plain text string.
    Raises ValueError on decryption failure or padding mismatch.
    """
    if not cipher_b64:
        return ""
    try:
        key_bytes = _derive_des3_key(key)
        cipher = DES3.new(key_bytes, DES3.MODE_ECB)
        data = base64.b64decode(cipher_b64)
        decrypted_padded = cipher.decrypt(data)
        decrypted_bytes = unpad(decrypted_padded, DES3.block_size, style="pkcs7")
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}") from e


def calc_md5_hash(value: str) -> str:
    """
    Calculates MD5 hash of value, matching C# CryptHelper.CalcMD5Hash.
    """
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def verify_md5_hash(value: str, expected_hash: str) -> bool:
    """
    Verifies value against expected MD5 hex string.
    """
    return calc_md5_hash(value).lower() == expected_hash.strip().lower()


class CryptoManager:
    """
    High-level crypto manager supporting both legacy TripleDES secrets
    and modern AES-256-GCM encrypted records.
    """

    @staticmethod
    def encrypt_secret(key: str, plain_text: str) -> str:
        """Encrypts a secret using TripleDES for full legacy DB compatibility."""
        return encrypt_des3(key, plain_text)

    @staticmethod
    def decrypt_secret(key: str, cipher_text: str) -> str:
        """Decrypts a secret stored in the legacy database."""
        return decrypt_des3(key, cipher_text)

    @staticmethod
    def encrypt_aes256(key_32bytes: bytes, plain_text: str) -> str:
        """
        Encrypts using modern AES-256-GCM.
        Returns base64 string formatted as nonce + ciphertext + tag.
        """
        aesgcm = AESGCM(key_32bytes)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("utf-8")

    @staticmethod
    def decrypt_aes256(key_32bytes: bytes, cipher_b64: str) -> str:
        """
        Decrypts modern AES-256-GCM ciphertext.
        """
        raw = base64.b64decode(cipher_b64)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key_32bytes)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
