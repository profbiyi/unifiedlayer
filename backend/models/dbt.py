"""
dbt ORM Models.

Defines database models for dbt project configuration and run tracking.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from backend.database import Base
from backend.utils.encrypted_type import EncryptedJSON


class DbtRunStatus(str, enum.Enum):
    """dbt run status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DbtProject(Base):
    """
    dbt Project configuration model.

    Represents a dbt project linked to an organization for transformation orchestration.
    """
    __tablename__ = "dbt_projects"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Git repository configuration
    git_repo_url = Column(String(500), nullable=False)  # e.g., https://github.com/org/dbt-project.git
    git_branch = Column(String(100), nullable=False, default="main")
    git_subdirectory = Column(String(255), nullable=True)  # Optional subdirectory within repo

    # Git credentials (encrypted for private repos)
    git_credentials = Column(EncryptedJSON, nullable=True)  # {"username": "...", "token": "..."}

    # dbt configuration
    dbt_version = Column(String(20), nullable=True)  # Optional specific dbt version
    target = Column(String(100), nullable=False, default="prod")  # dbt target profile
    profiles_yml = Column(Text, nullable=True)  # Custom profiles.yml content (encrypted in practice)

    # Environment variables for dbt (encrypted)
    env_vars = Column(EncryptedJSON, nullable=True)  # {"DBT_TARGET_SCHEMA": "analytics", ...}

    # Default run configuration
    default_select = Column(String(500), nullable=True)  # Default model selection, e.g., "+orders"
    default_exclude = Column(String(500), nullable=True)  # Default model exclusion

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="dbt_projects")
    pipeline_configs = relationship("PipelineDbtConfig", back_populates="dbt_project", cascade="all, delete-orphan")
    runs = relationship("DbtRun", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DbtProject(id={self.id}, name='{self.name}', repo='{self.git_repo_url}')>"


class PipelineDbtConfig(Base):
    """
    Pipeline dbt configuration model.

    Links a pipeline to a dbt project for post-load transformation.
    """
    __tablename__ = "pipeline_dbt_configs"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    dbt_project_id = Column(Integer, ForeignKey("dbt_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Override configuration (if different from project defaults)
    target = Column(String(100), nullable=True)  # Override dbt target
    select = Column(String(500), nullable=True)  # Model selection, e.g., "+orders +customers"
    exclude = Column(String(500), nullable=True)  # Model exclusion
    full_refresh = Column(Boolean, default=False, nullable=False)  # Run with --full-refresh

    # Run configuration
    run_on_success = Column(Boolean, default=True, nullable=False)  # Run dbt after successful pipeline load
    fail_pipeline_on_dbt_error = Column(Boolean, default=False, nullable=False)  # Mark pipeline failed if dbt fails

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pipeline = relationship("Pipeline", backref="dbt_config")
    dbt_project = relationship("DbtProject", back_populates="pipeline_configs")

    def __repr__(self):
        return f"<PipelineDbtConfig(pipeline_id={self.pipeline_id}, dbt_project_id={self.dbt_project_id})>"


class DbtRun(Base):
    """
    dbt run execution model.

    Tracks individual dbt command executions with logs and artifacts.
    """
    __tablename__ = "dbt_runs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    dbt_project_id = Column(Integer, ForeignKey("dbt_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True, index=True)  # Optional link to pipeline run

    # Celery task tracking
    celery_task_id = Column(String(255), nullable=True, index=True)  # Celery task ID for cancellation/monitoring

    # Run configuration
    command = Column(String(50), nullable=False)  # run, test, build, compile, etc.
    target = Column(String(100), nullable=True)
    select = Column(String(500), nullable=True)
    exclude = Column(String(500), nullable=True)
    full_refresh = Column(Boolean, default=False, nullable=False)

    # Execution status
    status = Column(SQLEnum(DbtRunStatus), default=DbtRunStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    models_ran = Column(Integer, nullable=True)
    models_passed = Column(Integer, nullable=True)
    models_failed = Column(Integer, nullable=True)
    models_skipped = Column(Integer, nullable=True)
    tests_passed = Column(Integer, nullable=True)
    tests_failed = Column(Integer, nullable=True)
    tests_warned = Column(Integer, nullable=True)

    # Logs and artifacts
    logs = Column(Text, nullable=True)  # Full console output
    run_results_json = Column(JSON, nullable=True)  # run_results.json content
    manifest_json = Column(JSON, nullable=True)  # manifest.json content (for lineage)

    # Error information
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    project = relationship("DbtProject", back_populates="runs")
    pipeline_run = relationship("PipelineRun", backref="dbt_runs")

    def __repr__(self):
        return f"<DbtRun(id={self.id}, project_id={self.dbt_project_id}, status='{self.status}')>"

    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
