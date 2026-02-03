"""
SQLAlchemy TypeDecorator for transparent JSON encryption at rest.

Usage:
    from backend.utils.encrypted_type import EncryptedJSON

    class MyModel(Base):
        config = Column(EncryptedJSON, nullable=False)

When ENCRYPTION_KEY is set, values are encrypted before storage and
decrypted on read. When ENCRYPTION_KEY is not set (dev/testing),
values pass through as plain JSON.
"""
import json
import logging

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


class EncryptedJSON(TypeDecorator):
    """
    A SQLAlchemy type that transparently encrypts/decrypts JSON data.

    Stores encrypted data as a JSON string value in the database.
    Falls back to plain JSON when ENCRYPTION_KEY is not configured,
    making it safe for development and testing environments.
    """

    impl = JSON
    cache_ok = True

    def _get_key(self):
        """Check if encryption is available."""
        from backend.config import settings
        return settings.ENCRYPTION_KEY

    def process_bind_param(self, value, dialect):
        """Encrypt the value before storing in the database."""
        if value is None:
            return None

        if not self._get_key():
            # No encryption key configured — store as plain JSON
            return value

        from backend.utils.encryption import encrypt_config
        # Encrypt the dict and store the ciphertext as a JSON string value
        return encrypt_config(value)

    def process_result_value(self, value, dialect):
        """Decrypt the value when reading from the database."""
        if value is None:
            return None

        if not self._get_key():
            # No encryption key — assume plain JSON
            return value

        # If the value is a string, it's encrypted ciphertext
        if isinstance(value, str):
            from backend.utils.encryption import decrypt_config
            try:
                return decrypt_config(value)
            except Exception:
                logger.warning(
                    "Failed to decrypt config value; returning as-is. "
                    "This may indicate the data was stored without encryption."
                )
                return value

        # If it's already a dict/list, it was stored as plain JSON
        return value
