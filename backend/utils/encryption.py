"""
Encryption utilities for sensitive configuration data.

Provides Fernet symmetric encryption (AES-128-CBC) for encrypting
DataSource and Destination config fields at rest.
"""
import json
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """
    Get a Fernet instance using the ENCRYPTION_KEY from settings.

    Raises:
        ValueError: If ENCRYPTION_KEY is not configured.
    """
    from backend.config import settings

    if not settings.ENCRYPTION_KEY:
        raise ValueError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_config(config: dict) -> str:
    """
    Encrypt a config dictionary.

    Serializes to JSON, then encrypts with Fernet.
    Returns a base64-encoded encrypted string.
    """
    fernet = _get_fernet()
    json_bytes = json.dumps(config, separators=(",", ":")).encode("utf-8")
    return fernet.encrypt(json_bytes).decode("utf-8")


def decrypt_config(encrypted: str) -> dict:
    """
    Decrypt an encrypted config string back to a dictionary.

    Args:
        encrypted: Base64-encoded Fernet token string.

    Returns:
        The original config dictionary.

    Raises:
        InvalidToken: If the token is invalid or the key is wrong.
    """
    fernet = _get_fernet()
    decrypted_bytes = fernet.decrypt(encrypted.encode("utf-8"))
    return json.loads(decrypted_bytes)


def encrypt_field(value: str) -> str:
    """
    Encrypt an individual string value.

    Args:
        value: Plain text string to encrypt.

    Returns:
        Base64-encoded encrypted string.
    """
    fernet = _get_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_field(encrypted: str) -> str:
    """
    Decrypt an individual encrypted string value.

    Args:
        encrypted: Base64-encoded Fernet token string.

    Returns:
        The original plain text string.
    """
    fernet = _get_fernet()
    return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
