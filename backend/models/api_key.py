"""
API Key ORM Model.

Provides the APIKey model for programmatic API access with
secure key hashing, scoped permissions, and expiration support.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class APIKey(Base):
    """
    API Keys for programmatic access.

    Features:
    - Secure key generation with prefix (dp_live_)
    - Key hashing (only hash stored, not plaintext)
    - Scoped permissions
    - Expiration support
    - Usage tracking
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(12), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    scopes = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")
    organization = relationship("Organization", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... for user_id={self.user_id}>"

    @property
    def is_expired(self):
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc) if self.expires_at.tzinfo is None else datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self):
        """Check if the key is active and not expired."""
        return self.is_active and not self.is_expired
