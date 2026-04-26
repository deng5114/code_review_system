"""AES-GCM encryption utility for sensitive data like API keys."""

from __future__ import annotations

import base64
import logging
import os
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

_NONCE_SIZE = 12  # AES-GCM standard nonce size (96 bits)


class AESEncryption:
    """AES-256-GCM authenticated encryption utility.

    Reads the encryption key from ``AES_ENCRYPTION_KEY`` environment variable,
    which must be a 64-character hex string (32 bytes). Falls back to
    Django signing when the key is not configured (dev mode).
    """

    def __init__(self, key_hex: Optional[str] = None) -> None:
        key_source = key_hex or os.environ.get("AES_ENCRYPTION_KEY", "")
        self._key: Optional[bytes] = None
        self._available = False

        if key_source and len(key_source) == 64:
            try:
                self._key = bytes.fromhex(key_source)
                self._available = True
            except ValueError:
                logger.warning("AES_ENCRYPTION_KEY is not valid hex, encryption disabled")

    @property
    def available(self) -> bool:
        return self._available

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-GCM.

        Returns a base64-encoded string containing ``nonce || ciphertext``.
        """
        if not self._available:
            raise RuntimeError("AES encryption not available: key not configured")

        nonce = secrets.token_bytes(_NONCE_SIZE)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a base64-encoded ``nonce || ciphertext`` string."""
        if not self._available:
            raise RuntimeError("AES encryption not available: key not configured")

        raw = base64.b64decode(encrypted)
        nonce = raw[:_NONCE_SIZE]
        ciphertext = raw[_NONCE_SIZE:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")

    @staticmethod
    def is_aes_encrypted(value: str) -> bool:
        """Heuristic: AES-GCM encrypted values are base64 and longer than 24 chars."""
        if len(value) < 24:
            return False
        try:
            decoded = base64.b64decode(value)
            return len(decoded) > _NONCE_SIZE
        except Exception:
            return False


def generate_key_hex() -> str:
    """Generate a random 32-byte key as a 64-character hex string."""
    return secrets.token_hex(32)
