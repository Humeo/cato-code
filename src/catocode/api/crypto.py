"""Fernet-based encryption for GitHub access tokens stored in the database."""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet

from ..config import get_session_secret_key


def _get_fernet() -> Fernet:
    """Derive a Fernet key from SESSION_SECRET_KEY."""
    raw = get_session_secret_key().encode()
    # Pad/truncate to 32 bytes, then base64url-encode (Fernet key format)
    padded = (raw * ((32 // len(raw)) + 1))[:32]
    key = base64.urlsafe_b64encode(padded)
    return Fernet(key)


def encrypt_token(token: str) -> str:
    """Encrypt a GitHub access token for storage."""
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored GitHub access token."""
    return _get_fernet().decrypt(encrypted.encode()).decode()
