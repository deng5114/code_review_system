"""Tests for AES-GCM encryption utility."""

import os
from unittest import mock

import pytest

from apps.common.services.crypto import AESEncryption, generate_key_hex


@pytest.fixture
def valid_key() -> str:
    return "a" * 64  # 32 bytes as 64 hex chars


@pytest.fixture
def aes(valid_key: str) -> AESEncryption:
    return AESEncryption(key_hex=valid_key)


class TestAESEncryption:
    """Unit tests for AESEncryption."""

    def test_encrypt_decrypt_roundtrip(self, aes: AESEncryption) -> None:
        plaintext = "sk-ant-api03-secret-key-12345"
        encrypted = aes.encrypt(plaintext)
        assert encrypted != plaintext
        assert aes.decrypt(encrypted) == plaintext

    def test_encrypt_produces_different_ciphertext(self, aes: AESEncryption) -> None:
        plaintext = "same-input-value"
        enc1 = aes.encrypt(plaintext)
        enc2 = aes.encrypt(plaintext)
        assert enc1 != enc2  # different nonce each time
        assert aes.decrypt(enc1) == plaintext
        assert aes.decrypt(enc2) == plaintext

    def test_encrypt_empty_string(self, aes: AESEncryption) -> None:
        encrypted = aes.encrypt("")
        assert aes.decrypt(encrypted) == ""

    def test_encrypt_unicode(self, aes: AESEncryption) -> None:
        plaintext = "密钥-🔑-unicode-test"
        encrypted = aes.encrypt(plaintext)
        assert aes.decrypt(encrypted) == plaintext

    def test_encrypt_long_key(self, aes: AESEncryption) -> None:
        plaintext = "x" * 500
        encrypted = aes.encrypt(plaintext)
        assert aes.decrypt(encrypted) == plaintext

    def test_decrypt_tampered_ciphertext_raises(self, aes: AESEncryption) -> None:
        import base64

        encrypted = aes.encrypt("secret")
        raw = bytearray(base64.b64decode(encrypted))
        raw[-1] ^= 0xFF  # flip last byte
        tampered = base64.b64encode(raw).decode("ascii")
        with pytest.raises(Exception):
            aes.decrypt(tampered)

    def test_available_with_valid_key(self, aes: AESEncryption) -> None:
        assert aes.available is True

    def test_not_available_without_key(self) -> None:
        aes = AESEncryption(key_hex="")
        assert aes.available is False

    def test_not_available_with_short_key(self) -> None:
        aes = AESEncryption(key_hex="abcd")
        assert aes.available is False

    def test_not_available_with_invalid_hex(self) -> None:
        aes = AESEncryption(key_hex="z" * 64)
        assert aes.available is False

    def test_encrypt_raises_when_unavailable(self) -> None:
        aes = AESEncryption(key_hex="")
        with pytest.raises(RuntimeError, match="not available"):
            aes.encrypt("test")

    def test_decrypt_raises_when_unavailable(self) -> None:
        aes = AESEncryption(key_hex="")
        with pytest.raises(RuntimeError, match="not available"):
            aes.decrypt("test")

    def test_reads_key_from_env(self) -> None:
        key = generate_key_hex()
        with mock.patch.dict(os.environ, {"AES_ENCRYPTION_KEY": key}):
            aes = AESEncryption()
            assert aes.available is True
            encrypted = aes.encrypt("env-key-test")
            assert aes.decrypt(encrypted) == "env-key-test"


class TestIsAESEncrypted:
    """Tests for the AES-encrypted detection heuristic."""

    def test_detects_encrypted_value(self, aes: AESEncryption) -> None:
        encrypted = aes.encrypt("test")
        assert AESEncryption.is_aes_encrypted(encrypted) is True

    def test_short_string_not_encrypted(self) -> None:
        assert AESEncryption.is_aes_encrypted("short") is False

    def test_django_signed_not_encrypted(self) -> None:
        signed = "my-key:value:abc123sig"
        assert AESEncryption.is_aes_encrypted(signed) is False

    def test_invalid_base64_not_encrypted(self) -> None:
        assert AESEncryption.is_aes_encrypted("not!valid!base64!here!!") is False


class TestGenerateKeyHex:
    """Tests for key generation utility."""

    def test_generates_64_char_hex(self) -> None:
        key = generate_key_hex()
        assert len(key) == 64
        int(key, 16)  # must be valid hex

    def test_generates_unique_keys(self) -> None:
        keys = {generate_key_hex() for _ in range(10)}
        assert len(keys) == 10

    def test_generated_key_works(self) -> None:
        key = generate_key_hex()
        aes = AESEncryption(key_hex=key)
        assert aes.available is True
        encrypted = aes.encrypt("test")
        assert aes.decrypt(encrypted) == "test"
