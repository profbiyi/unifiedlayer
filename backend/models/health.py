"""
Resource Health ORM Model.

Stores health check snapshots for sources and pipelines.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from backend.database import Base


class HealthStatus(str, enum.Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ResourceType(str, enum.Enum):
    """Resource type enumeration."""
    SOURCE = "source"
    PIPELINE = "pipeline"
    DESTINATION = "destination"


class ResourceHealth(Base):
    """
    Resource Health model.

    Stores health check snapshots for sources, pipelines, and destinations.
    Each health check stores the current health status, score, and any issues detected.
    """
    __tablename__ = "resource_health"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Resource identification
    resource_type = Column(SQLEnum(ResourceType), nullable=False, index=True)
    resource_id = Column(Integer, nullable=False, index=True)  # Internal ID of the source/pipeline/destination

    # Health status
    status = Column(SQLEnum(HealthStatus), nullable=False, default=HealthStatus.UNKNOWN, index=True)
    score = Column(Float, nullable=False, default=0.0)  # 0-100 health score

    # Health check details
    last_checked_at = Column(DateTime, nullable=True)
    next_check_at = Column(DateTime, nullable=True)

    # Issues detected (JSON array of issue objects)
    # Each issue: {"code": "CONN_FAILED", "message": "Connection timed out", "severity": "critical"}
    issues = Column(JSONB, nullable=False, default=list)

    # Detailed metrics (JSON object with health check metrics)
    # e.g., {"connection_test": {"success": false, "latency_ms": null, "error": "timeout"},
    #        "token_expiry": {"days_until_expiry": 5, "warning": true},
    #        "success_rate": {"last_10_runs": 0.8, "last_24h_runs": 0.75}}
    metrics = Column(JSONB, nullable=False, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Composite index for efficient lookups
    __table_args__ = (
        Index('ix_resource_health_org_type_resource', 'organization_id', 'resource_type', 'resource_id'),
    )

    def __repr__(self):
        return f"<ResourceHealth(id={self.id}, type={self.resource_type}, resource_id={self.resource_id}, status={self.status})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.public_id),
            "resource_type": self.resource_type.value if self.resource_type else None,
            "resource_id": self.resource_id,
            "status": self.status.value if self.status else None,
            "score": self.score,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "next_check_at": self.next_check_at.isoformat() if self.next_check_at else None,
            "issues": self.issues or [],
            "metrics": self.metrics or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HealthCheckLog(Base):
    """
    Health Check Log model.

    Stores historical health check results for auditing and trending.
    """
    __tablename__ = "health_check_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Resource identification
    resource_type = Column(SQLEnum(ResourceType), nullable=False, index=True)
    resource_id = Column(Integer, nullable=False, index=True)

    # Health check result
    status = Column(SQLEnum(HealthStatus), nullable=False)
    score = Column(Float, nullable=False)
    issues = Column(JSONB, nullable=False, default=list)
    metrics = Column(JSONB, nullable=False, default=dict)

    # Check metadata
    check_type = Column(String(50), nullable=True)  # e.g., "scheduled", "manual", "on_demand"
    duration_ms = Column(Integer, nullable=True)  # How long the health check took

    # Timestamp
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Index for efficient time-series queries
    __table_args__ = (
        Index('ix_health_log_org_resource_time', 'organization_id', 'resource_type', 'resource_id', 'checked_at'),
    )

    def __repr__(self):
        return f"<HealthCheckLog(id={self.id}, type={self.resource_type}, status={self.status})>"
