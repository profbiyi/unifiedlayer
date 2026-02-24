"""
dbt Orchestration API routes.

Provides endpoints for managing dbt projects, runs, and pipeline configurations.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
import re
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator, computed_field

from backend.database import get_db
from backend.models.pipeline import User, Pipeline
from backend.models.dbt import DbtProject, PipelineDbtConfig, DbtRun, DbtRunStatus
from backend.auth import get_current_user
from backend.rbac.permissions import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dbt", tags=["dbt Orchestration"])

# ==================== PYDANTIC SCHEMAS ====================


class GitCredentials(BaseModel):
    """Git credentials for private repository access."""
    username: Optional[str] = None
    token: Optional[str] = None
    ssh_key: Optional[str] = None


class DbtProjectCreate(BaseModel):
    """dbt project creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    # Git repository configuration
    git_repo_url: str = Field(..., min_length=1, max_length=500)
    git_branch: str = Field(default="main", max_length=100)
    git_subdirectory: Optional[str] = Field(None, max_length=255)

    # Git credentials for private repos
    git_credentials: Optional[GitCredentials] = None

    # dbt configuration
    dbt_version: Optional[str] = Field(None, max_length=20)
    target: str = Field(default="prod", max_length=100)
    profiles_yml: Optional[str] = None

    # Environment variables
    env_vars: Optional[Dict[str, str]] = None

    # Default run configuration
    default_select: Optional[str] = Field(None, max_length=500)
    default_exclude: Optional[str] = Field(None, max_length=500)

    @field_validator('git_repo_url')
    @classmethod
    def validate_git_url(cls, v: str) -> str:
        """Validate git repository URL format."""
        # Support HTTPS and SSH git URLs
        https_pattern = r'^https://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+/.*\.git$'
        ssh_pattern = r'^git@[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+:.*\.git$'

        if not (re.match(https_pattern, v) or re.match(ssh_pattern, v)):
            # Also allow URLs without .git suffix
            https_pattern_no_suffix = r'^https://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+/.*$'
            ssh_pattern_no_suffix = r'^git@[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+:.*$'
            if not (re.match(https_pattern_no_suffix, v) or re.match(ssh_pattern_no_suffix, v)):
                raise ValueError('Invalid git repository URL. Must be HTTPS or SSH format.')
        return v

    @field_validator('dbt_version')
    @classmethod
    def validate_dbt_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate dbt version format."""
        if v is not None:
            version_pattern = r'^\d+\.\d+(\.\d+)?$'
            if not re.match(version_pattern, v):
                raise ValueError('Invalid dbt version format. Expected format: X.Y or X.Y.Z')
        return v


class DbtProjectUpdate(BaseModel):
    """dbt project update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    git_repo_url: Optional[str] = Field(None, min_length=1, max_length=500)
    git_branch: Optional[str] = Field(None, max_length=100)
    git_subdirectory: Optional[str] = Field(None, max_length=255)
    git_credentials: Optional[GitCredentials] = None
    dbt_version: Optional[str] = Field(None, max_length=20)
    target: Optional[str] = Field(None, max_length=100)
    profiles_yml: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    default_select: Optional[str] = Field(None, max_length=500)
    default_exclude: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class DbtProjectResponse(BaseModel):
    """dbt project response schema."""
    public_id: UUID
    name: str
    description: Optional[str]
    git_repo_url: str
    git_branch: str
    git_subdirectory: Optional[str]
    dbt_version: Optional[str]
    target: str
    default_select: Optional[str]
    default_exclude: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


class DbtRunCreate(BaseModel):
    """dbt run trigger request schema."""
    command: str = Field(default="run", pattern=r'^(run|test|build|compile|seed|snapshot|docs|source)$')
    target: Optional[str] = Field(None, max_length=100)
    select: Optional[str] = Field(None, max_length=500)
    exclude: Optional[str] = Field(None, max_length=500)
    full_refresh: bool = False


class DbtRunResponse(BaseModel):
    """dbt run response schema."""
    public_id: UUID
    dbt_project_id: int
    pipeline_run_id: Optional[int]
    celery_task_id: Optional[str]
    command: str
    target: Optional[str]
    select: Optional[str]
    exclude: Optional[str]
    full_refresh: bool
    status: DbtRunStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    models_ran: Optional[int]
    models_passed: Optional[int]
    models_failed: Optional[int]
    models_skipped: Optional[int]
    tests_passed: Optional[int]
    tests_failed: Optional[int]
    tests_warned: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


class DbtRunDetailResponse(DbtRunResponse):
    """dbt run detail response with logs."""
    logs: Optional[str]
    run_results_json: Optional[Dict[str, Any]]


class DbtModelInfo(BaseModel):
    """dbt model information from manifest."""
    unique_id: str
    name: str
    description: Optional[str]
    resource_type: str
    schema_name: Optional[str] = Field(None, alias="schema")
    database: Optional[str]
    materialized: Optional[str]
    depends_on: List[str] = []
    tags: List[str] = []

    class Config:
        populate_by_name = True


class PipelineDbtConfigCreate(BaseModel):
    """Pipeline dbt configuration creation schema."""
    dbt_project_id: str  # UUID string
    target: Optional[str] = Field(None, max_length=100)
    select: Optional[str] = Field(None, max_length=500)
    exclude: Optional[str] = Field(None, max_length=500)
    full_refresh: bool = False
    run_on_success: bool = True
    fail_pipeline_on_dbt_error: bool = False


class PipelineDbtConfigUpdate(BaseModel):
    """Pipeline dbt configuration update schema."""
    dbt_project_id: Optional[str] = None  # UUID string
    target: Optional[str] = Field(None, max_length=100)
    select: Optional[str] = Field(None, max_length=500)
    exclude: Optional[str] = Field(None, max_length=500)
    full_refresh: Optional[bool] = None
    run_on_success: Optional[bool] = None
    fail_pipeline_on_dbt_error: Optional[bool] = None
    is_active: Optional[bool] = None


class PipelineDbtConfigResponse(BaseModel):
    """Pipeline dbt configuration response schema."""
    id: int
    pipeline_id: int
    dbt_project_id: int
    dbt_project_name: Optional[str] = None
    target: Optional[str]
    select: Optional[str]
    exclude: Optional[str]
    full_refresh: bool
    run_on_success: bool
    fail_pipeline_on_dbt_error: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestConnectionResult(BaseModel):
    """Git connection test result."""
    success: bool
    message: str
    branch_exists: bool = False
    subdirectory_exists: bool = False
    has_dbt_project: bool = False


# ==================== HELPER FUNCTIONS ====================


def get_dbt_project_or_404(
    project_id: str,
    db: Session,
    organization_id: int
) -> DbtProject:
    """Get dbt project by public_id or raise 404."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    project = db.query(DbtProject).filter(
        DbtProject.public_id == project_uuid,
        DbtProject.organization_id == organization_id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="dbt project not found",
        )

    return project


def get_pipeline_or_404(
    pipeline_id: str,
    db: Session,
    organization_id: int
) -> Pipeline:
    """Get pipeline by public_id or raise 404."""
    try:
        pipeline_uuid = UUID(pipeline_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pipeline ID format",
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.public_id == pipeline_uuid,
        Pipeline.organization_id == organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found",
        )

    return pipeline


# ==================== DBT PROJECT ENDPOINTS ====================


@router.get("/projects", response_model=List[DbtProjectResponse])
@require_permission("dbt_project", "read")
async def list_dbt_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all dbt projects for the current user's organization.

    **Requires:** dbt_project.read permission
    """
    query = db.query(DbtProject).filter(
        DbtProject.organization_id == current_user.organization_id
    )

    if is_active is not None:
        query = query.filter(DbtProject.is_active == is_active)

    projects = query.order_by(DbtProject.created_at.desc()).offset(skip).limit(limit).all()
    return projects


@router.post("/projects", response_model=DbtProjectResponse, status_code=status.HTTP_201_CREATED)
@require_permission("dbt_project", "create")
async def create_dbt_project(
    project_data: DbtProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new dbt project.

    **Requires:** dbt_project.create permission
    """
    # Check for duplicate name in organization
    existing = db.query(DbtProject).filter(
        DbtProject.organization_id == current_user.organization_id,
        DbtProject.name == project_data.name,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A dbt project with name '{project_data.name}' already exists",
        )

    project = DbtProject(
        organization_id=current_user.organization_id,
        name=project_data.name,
        description=project_data.description,
        git_repo_url=project_data.git_repo_url,
        git_branch=project_data.git_branch,
        git_subdirectory=project_data.git_subdirectory,
        git_credentials=project_data.git_credentials.model_dump() if project_data.git_credentials else None,
        dbt_version=project_data.dbt_version,
        target=project_data.target,
        profiles_yml=project_data.profiles_yml,
        env_vars=project_data.env_vars,
        default_select=project_data.default_select,
        default_exclude=project_data.default_exclude,
        is_active=True,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    logger.info(f"dbt project created: {project.id} - {project.name} by user {current_user.id}")
    return project


@router.get("/projects/{project_id}", response_model=DbtProjectResponse)
@require_permission("dbt_project", "read")
async def get_dbt_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific dbt project by ID.

    **Requires:** dbt_project.read permission
    """
    project = get_dbt_project_or_404(project_id, db, current_user.organization_id)
    return project


@router.put("/projects/{project_id}", response_model=DbtProjectResponse)
@require_permission("dbt_project", "update")
async def update_dbt_project(
    project_id: str,
    project_data: DbtProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing dbt project.

    **Requires:** dbt_project.update permission
    """
    project = get_dbt_project_or_404(project_id, db, current_user.organization_id)

    # Check for duplicate name if changing name
    if project_data.name and project_data.name != project.name:
        existing = db.query(DbtProject).filter(
            DbtProject.organization_id == current_user.organization_id,
            DbtProject.name == project_data.name,
            DbtProject.id != project.id,
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A dbt project with name '{project_data.name}' already exists",
            )

    update_data = project_data.model_dump(exclude_unset=True)

    # Handle git_credentials separately
    if 'git_credentials' in update_data:
        creds = update_data.pop('git_credentials')
        if creds:
            project.git_credentials = creds if isinstance(creds, dict) else creds.model_dump()
        else:
            project.git_credentials = None

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    logger.info(f"dbt project updated: {project.id} - {project.name} by user {current_user.id}")
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("dbt_project", "delete")
async def delete_dbt_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a dbt project.

    **Requires:** dbt_project.delete permission

    Note: This will also delete all associated pipeline dbt configs and runs.
    """
    project = get_dbt_project_or_404(project_id, db, current_user.organization_id)

    # Check for active pipeline configs using this project
    active_configs = db.query(PipelineDbtConfig).filter(
        PipelineDbtConfig.dbt_project_id == project.id,
        PipelineDbtConfig.is_active,
    ).count()

    if active_configs > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete project. {active_configs} pipeline(s) are using this dbt project. Remove the dbt configurations first.",
        )

    db.delete(project)
    db.commit()

    logger.info(f"dbt project deleted: {project.id} by user {current_user.id}")
    return None


@router.post("/projects/{project_id}/test-connection", response_model=TestConnectionResult)
@require_permission("dbt_project", "read")
async def test_git_connection(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test git repository connection for a dbt project.

    **Requires:** dbt_project.read permission

    Validates:
    - Repository is accessible
    - Branch exists
    - Subdirectory exists (if specified)
    - dbt_project.yml is present
    """
    project = get_dbt_project_or_404(project_id, db, current_user.organization_id)

    try:
        result = _test_git_connection(
            git_repo_url=project.git_repo_url,
            git_branch=project.git_branch,
            git_subdirectory=project.git_subdirectory,
            git_credentials=project.git_credentials,
        )
        return result
    except Exception as e:
        logger.error(f"Git connection test failed for project {project.id}: {str(e)}")
        return TestConnectionResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            branch_exists=False,
            subdirectory_exists=False,
            has_dbt_project=False,
        )


def _test_git_connection(
    git_repo_url: str,
    git_branch: str,
    git_subdirectory: Optional[str],
    git_credentials: Optional[Dict[str, Any]],
) -> TestConnectionResult:
    """
    Test git repository connection.

    This is a simplified implementation. In production, you would:
    1. Clone the repository (shallow) or use git ls-remote
    2. Check if the branch exists
    3. Check if the subdirectory exists
    4. Verify dbt_project.yml is present

    Security note: Git credentials are passed via environment variables
    to avoid exposure in error messages or process listings.
    """
    import subprocess
    import tempfile
    import os

    try:
        # Build environment with credentials (safer than embedding in URL)
        env = os.environ.copy()
        use_url = git_repo_url

        if git_credentials:
            if git_credentials.get('token'):
                # For HTTPS URLs, use credential helper via environment
                if git_repo_url.startswith('https://'):
                    username = git_credentials.get('username', 'oauth2')
                    token = git_credentials['token']
                    # Use GIT_ASKPASS with a helper script to provide credentials
                    # This avoids exposing tokens in URLs (which appear in logs/errors)
                    env['GIT_USERNAME'] = username
                    env['GIT_PASSWORD'] = token
                    # Configure git to use credential from environment
                    env['GIT_TERMINAL_PROMPT'] = '0'
                    # Use credential.helper to read from environment
                    env['GIT_CONFIG_COUNT'] = '1'
                    env['GIT_CONFIG_KEY_0'] = 'credential.helper'
                    env['GIT_CONFIG_VALUE_0'] = '!f() { echo "username=$GIT_USERNAME"; echo "password=$GIT_PASSWORD"; }; f'

        # Test with git ls-remote (doesn't clone, just checks access)
        result = subprocess.run(
            ['git', 'ls-remote', '--heads', use_url, git_branch],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        if result.returncode != 0:
            # Sanitize error message to remove any potential credential leaks
            error_msg = result.stderr.strip()
            # Remove any accidentally leaked credentials from error message
            if git_credentials and git_credentials.get('token'):
                error_msg = error_msg.replace(git_credentials['token'], '[REDACTED]')
            return TestConnectionResult(
                success=False,
                message=f"Failed to access repository: {error_msg}",
                branch_exists=False,
            )

        branch_exists = git_branch in result.stdout

        if not branch_exists:
            return TestConnectionResult(
                success=False,
                message=f"Branch '{git_branch}' not found in repository",
                branch_exists=False,
            )

        # For deeper validation (subdirectory & dbt_project.yml), we'd need to clone
        # This is a simplified check - in production, consider using GitHub/GitLab APIs
        # or a shallow clone

        # Shallow clone to temp directory for validation
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_result = subprocess.run(
                ['git', 'clone', '--depth', '1', '--branch', git_branch, use_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )

            if clone_result.returncode != 0:
                return TestConnectionResult(
                    success=True,
                    message="Repository accessible, but could not verify contents",
                    branch_exists=True,
                    subdirectory_exists=False,
                    has_dbt_project=False,
                )

            # Check subdirectory
            check_dir = tmpdir
            if git_subdirectory:
                check_dir = os.path.join(tmpdir, git_subdirectory)
                subdirectory_exists = os.path.isdir(check_dir)
                if not subdirectory_exists:
                    return TestConnectionResult(
                        success=False,
                        message=f"Subdirectory '{git_subdirectory}' not found",
                        branch_exists=True,
                        subdirectory_exists=False,
                    )
            else:
                subdirectory_exists = True

            # Check for dbt_project.yml
            dbt_project_file = os.path.join(check_dir, 'dbt_project.yml')
            has_dbt_project = os.path.isfile(dbt_project_file)

            if not has_dbt_project:
                return TestConnectionResult(
                    success=False,
                    message="dbt_project.yml not found in the specified location",
                    branch_exists=True,
                    subdirectory_exists=subdirectory_exists,
                    has_dbt_project=False,
                )

            return TestConnectionResult(
                success=True,
                message="Successfully connected to repository and found dbt project",
                branch_exists=True,
                subdirectory_exists=subdirectory_exists,
                has_dbt_project=True,
            )

    except subprocess.TimeoutExpired:
        return TestConnectionResult(
            success=False,
            message="Connection timed out",
        )
    except Exception as e:
        # Sanitize error message to prevent credential leaks
        error_msg = str(e)
        if git_credentials and git_credentials.get('token'):
            error_msg = error_msg.replace(git_credentials['token'], '[REDACTED]')
        if git_credentials and git_credentials.get('ssh_key'):
            error_msg = error_msg.replace(git_credentials['ssh_key'], '[REDACTED]')
        return TestConnectionResult(
            success=False,
            message=f"Error: {error_msg}",
        )


@router.get("/projects/{project_id}/models", response_model=List[DbtModelInfo])
@require_permission("dbt_project", "read")
async def list_dbt_models(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List available dbt models from the project manifest.

    **Requires:** dbt_project.read permission

    Returns models parsed from the most recent successful run's manifest.json.
    If no manifest is available, attempts to compile the project.
    """
    project = get_dbt_project_or_404(project_id, db, current_user.organization_id)

    # Get the most recent successful run with manifest
    latest_run = db.query(DbtRun).filter(
        DbtRun.dbt_project_id == project.id,
        DbtRun.status == DbtRunStatus.COMPLETED,
        DbtRun.manifest_json.isnot(None),
    ).order_by(DbtRun.completed_at.desc()).first()

    if not latest_run or not latest_run.manifest_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No manifest available. Run 'dbt compile' first to generate the manifest.",
        )

    models = _parse_manifest_models(latest_run.manifest_json)
    return models


def _parse_manifest_models(manifest: Dict[str, Any]) -> List[DbtModelInfo]:
    """Parse dbt models from manifest.json."""
    models = []

    nodes = manifest.get('nodes', {})
    for unique_id, node in nodes.items():
        resource_type = node.get('resource_type', '')
        if resource_type not in ('model', 'seed', 'snapshot', 'source'):
            continue

        depends_on = []
        if 'depends_on' in node:
            depends_on = node['depends_on'].get('nodes', [])

        models.append(DbtModelInfo(
            unique_id=unique_id,
            name=node.get('name', ''),
            description=node.get('description'),
            resource_type=resource_type,
            schema_name=node.get('schema'),
            database=node.get('database'),
            materialized=node.get('config', {}).get('materialized'),
            depends_on=depends_on,
            tags=node.get('tags', []),
        ))

    return models


# ==================== DBT RUN ENDPOINTS ====================


@router.post("/projects/{project_id}/run", response_model=DbtRunResponse, status_code=status.HTTP_202_ACCEPTED)
@require_permission("dbt_project", "execute")
async def trigger_dbt_run(
    project_id: str,
    run_config: DbtRunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger a dbt run for a project.

    **Requires:** dbt_project.execute permission

    Supported commands:
    - run: Execute models
    - test: Run tests
    - build: Run models and tests
    - compile: Compile models without execution
    - seed: Load seed data
    - snapshot: Run snapshots
    - docs: Generate documentation
    - source: Run source freshness checks

    The dbt execution runs as a background Celery task with:
    - 30-minute timeout
    - Up to 3 retries with exponential backoff
    - Task cancellation support via /runs/{run_id}/cancel
    """
    from backend.tasks.dbt_tasks import execute_dbt_run

    project = get_dbt_project_or_404(project_id, db, current_user.organization_id)

    if not project.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dbt project is not active",
        )

    # Create dbt run record
    dbt_run = DbtRun(
        dbt_project_id=project.id,
        command=run_config.command,
        target=run_config.target or project.target,
        select=run_config.select or project.default_select,
        exclude=run_config.exclude or project.default_exclude,
        full_refresh=run_config.full_refresh,
        status=DbtRunStatus.PENDING,
    )

    db.add(dbt_run)
    db.commit()
    db.refresh(dbt_run)

    logger.info(f"dbt run triggered: {dbt_run.id} for project {project.id} by user {current_user.id}")

    # Submit run to Celery background worker
    task = execute_dbt_run.delay(dbt_run.id, project.id)

    # Store Celery task ID for cancellation/monitoring
    dbt_run.celery_task_id = task.id
    db.commit()
    db.refresh(dbt_run)

    logger.info(f"dbt run {dbt_run.id} submitted to Celery with task_id={task.id}")

    return dbt_run


@router.post("/runs/{run_id}/cancel", response_model=DbtRunResponse)
@require_permission("dbt_project", "execute")
async def cancel_dbt_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a running or pending dbt execution.

    **Requires:** dbt_project.execute permission

    This endpoint will:
    1. Revoke the Celery task if it's still pending or running
    2. Update the run status to CANCELLED
    """
    from backend.celery_app import celery_app

    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run ID format",
        )

    run = db.query(DbtRun).join(DbtProject).filter(
        DbtRun.public_id == run_uuid,
        DbtProject.organization_id == current_user.organization_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="dbt run not found",
        )

    # Check if run is already in a terminal state
    if run.status in (DbtRunStatus.COMPLETED, DbtRunStatus.FAILED, DbtRunStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel run in '{run.status.value}' state",
        )

    # Revoke the Celery task if we have a task ID
    if run.celery_task_id:
        logger.info(f"Revoking Celery task {run.celery_task_id} for dbt run {run.id}")
        celery_app.control.revoke(run.celery_task_id, terminate=True, signal="SIGTERM")

    # Update run status
    run.status = DbtRunStatus.CANCELLED
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = f"Cancelled by user {current_user.email}"
    if run.started_at:
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()

    db.commit()
    db.refresh(run)

    logger.info(f"dbt run {run.id} cancelled by user {current_user.id}")

    return run


@router.get("/runs", response_model=List[DbtRunResponse])
@require_permission("dbt_project", "read")
async def list_dbt_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status_filter: Optional[DbtRunStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List dbt runs for the organization.

    **Requires:** dbt_project.read permission
    """
    query = db.query(DbtRun).join(DbtProject).filter(
        DbtProject.organization_id == current_user.organization_id
    )

    if project_id:
        project = get_dbt_project_or_404(project_id, db, current_user.organization_id)
        query = query.filter(DbtRun.dbt_project_id == project.id)

    if status_filter:
        query = query.filter(DbtRun.status == status_filter)

    runs = query.order_by(DbtRun.created_at.desc()).offset(skip).limit(limit).all()
    return runs


@router.get("/runs/{run_id}", response_model=DbtRunDetailResponse)
@require_permission("dbt_project", "read")
async def get_dbt_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dbt run details with logs.

    **Requires:** dbt_project.read permission
    """
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run ID format",
        )

    run = db.query(DbtRun).join(DbtProject).filter(
        DbtRun.public_id == run_uuid,
        DbtProject.organization_id == current_user.organization_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="dbt run not found",
        )

    return run


# ==================== PIPELINE DBT CONFIG ENDPOINTS ====================

# Create a separate router for pipeline-specific endpoints
pipeline_dbt_router = APIRouter(prefix="/pipelines", tags=["Pipeline dbt Config"])


@pipeline_dbt_router.get("/{pipeline_id}/dbt-config", response_model=PipelineDbtConfigResponse)
@require_permission("pipeline", "read")
async def get_pipeline_dbt_config(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get pipeline's dbt configuration.

    **Requires:** pipeline.read permission
    """
    pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)

    config = db.query(PipelineDbtConfig).filter(
        PipelineDbtConfig.pipeline_id == pipeline.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline does not have a dbt configuration",
        )

    # Add project name for convenience
    response_data = {
        "id": config.id,
        "pipeline_id": config.pipeline_id,
        "dbt_project_id": config.dbt_project_id,
        "dbt_project_name": config.dbt_project.name if config.dbt_project else None,
        "target": config.target,
        "select": config.select,
        "exclude": config.exclude,
        "full_refresh": config.full_refresh,
        "run_on_success": config.run_on_success,
        "fail_pipeline_on_dbt_error": config.fail_pipeline_on_dbt_error,
        "is_active": config.is_active,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }

    return PipelineDbtConfigResponse(**response_data)


@pipeline_dbt_router.put("/{pipeline_id}/dbt-config", response_model=PipelineDbtConfigResponse)
@require_permission("pipeline", "update")
async def set_pipeline_dbt_config(
    pipeline_id: str,
    config_data: PipelineDbtConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set or update pipeline's dbt configuration.

    **Requires:** pipeline.update permission

    If a configuration already exists, it will be updated.
    Otherwise, a new configuration will be created.
    """
    pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)

    # Validate dbt project belongs to same organization
    dbt_project = get_dbt_project_or_404(
        config_data.dbt_project_id,
        db,
        current_user.organization_id
    )

    # Check for existing config
    existing_config = db.query(PipelineDbtConfig).filter(
        PipelineDbtConfig.pipeline_id == pipeline.id
    ).first()

    if existing_config:
        # Update existing
        existing_config.dbt_project_id = dbt_project.id
        existing_config.target = config_data.target
        existing_config.select = config_data.select
        existing_config.exclude = config_data.exclude
        existing_config.full_refresh = config_data.full_refresh
        existing_config.run_on_success = config_data.run_on_success
        existing_config.fail_pipeline_on_dbt_error = config_data.fail_pipeline_on_dbt_error
        existing_config.is_active = True

        db.commit()
        db.refresh(existing_config)
        config = existing_config
        logger.info(f"Pipeline dbt config updated: pipeline={pipeline.id}, project={dbt_project.id}")
    else:
        # Create new
        config = PipelineDbtConfig(
            pipeline_id=pipeline.id,
            dbt_project_id=dbt_project.id,
            target=config_data.target,
            select=config_data.select,
            exclude=config_data.exclude,
            full_refresh=config_data.full_refresh,
            run_on_success=config_data.run_on_success,
            fail_pipeline_on_dbt_error=config_data.fail_pipeline_on_dbt_error,
            is_active=True,
        )

        db.add(config)
        db.commit()
        db.refresh(config)
        logger.info(f"Pipeline dbt config created: pipeline={pipeline.id}, project={dbt_project.id}")

    response_data = {
        "id": config.id,
        "pipeline_id": config.pipeline_id,
        "dbt_project_id": config.dbt_project_id,
        "dbt_project_name": dbt_project.name,
        "target": config.target,
        "select": config.select,
        "exclude": config.exclude,
        "full_refresh": config.full_refresh,
        "run_on_success": config.run_on_success,
        "fail_pipeline_on_dbt_error": config.fail_pipeline_on_dbt_error,
        "is_active": config.is_active,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }

    return PipelineDbtConfigResponse(**response_data)


@pipeline_dbt_router.delete("/{pipeline_id}/dbt-config", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("pipeline", "update")
async def delete_pipeline_dbt_config(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove dbt configuration from a pipeline.

    **Requires:** pipeline.update permission
    """
    pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)

    config = db.query(PipelineDbtConfig).filter(
        PipelineDbtConfig.pipeline_id == pipeline.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline does not have a dbt configuration",
        )

    db.delete(config)
    db.commit()

    logger.info(f"Pipeline dbt config deleted: pipeline={pipeline.id}")
    return None
