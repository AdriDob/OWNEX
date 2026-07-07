"""Shared vault encryption — AES-256-GCM with key file in ~/.orion.

Used by IdentityVault, TokenService, and SessionStore to encrypt data at rest.
Key generated on first access, stored in ~/.orion/identity_vault.key (chmod 600).
"""

from __future__ import annotations

import base64
import logging
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("cateye.vault_crypto")

_AES_NONCE_BYTES = 12
_VAULT_KEY: bytes | None = None


def _get_key_dir() -> str:
    home = os.environ.get("HOME", os.environ.get("USERPROFILE", "."))
    return os.path.join(home, ".orion")


def _get_key_path() -> str:
    return os.path.join(_get_key_dir(), "identity_vault.key")


def get_vault_key() -> bytes:
    global _VAULT_KEY
    if _VAULT_KEY is not None:
        return _VAULT_KEY

    key_path = _get_key_path()
    if os.path.exists(key_path):
        try:
            with open(key_path, "rb") as f:
                _VAULT_KEY = f.read().strip()
            if len(_VAULT_KEY) == 32:
                return _VAULT_KEY
        except Exception:
            logger.warning("Failed to read vault key, generating new one")

    _VAULT_KEY = secrets.token_bytes(32)
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "wb") as f:
        f.write(_VAULT_KEY)
    os.chmod(key_path, 0o600)
    return _VAULT_KEY


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    key = get_vault_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(_AES_NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(payload: str) -> str:
    if not payload:
        return ""
    key = get_vault_key()
    try:
        raw = base64.b64decode(payload.encode("ascii"))
        if len(raw) < _AES_NONCE_BYTES + 16:
            return ""
        nonce = raw[:_AES_NONCE_BYTES]
        ciphertext = raw[_AES_NONCE_BYTES:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        logger.warning("Decryption failed")
        return ""
