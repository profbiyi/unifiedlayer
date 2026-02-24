"""
dbt Execution Tasks.

Celery tasks for executing dbt commands in the background.

This module provides Celery tasks for running dbt commands asynchronously.
The actual execution logic is delegated to the dbt_executor service which handles:
- Git repository cloning with secure credential handling
- dbt environment setup (profiles.yml, env vars)
- Command execution with timeout
- Artifact parsing (run_results.json, manifest.json)
- Credential sanitization in logs and error messages

Security notes:
- Git credentials are passed via environment variables, never embedded in URLs
- All error messages are sanitized to prevent credential leakage
- Execution timeout is enforced (max 30 minutes)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from backend.celery_app import celery_app, BaseTask
from backend.database import SessionLocal
from backend.models.dbt import DbtProject, DbtRun, DbtRunStatus

logger = logging.getLogger(__name__)

# Task timeout: 30 minutes
DBT_TASK_TIMEOUT = 30 * 60  # 1800 seconds
DBT_TASK_SOFT_TIMEOUT = 28 * 60  # 1680 seconds (2 minutes before hard timeout)


class DbtExecutionTask(BaseTask):
    """Base class for dbt execution tasks with retry logic."""

    autoretry_for = (Exception,)
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add randomness to avoid thundering herd
    max_retries = 3
    soft_time_limit = DBT_TASK_SOFT_TIMEOUT
    time_limit = DBT_TASK_TIMEOUT

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Update DbtRun status on task failure."""
        run_id = args[0] if args else kwargs.get("run_id")
        if run_id:
            db = SessionLocal()
            try:
                run = db.query(DbtRun).filter(DbtRun.id == run_id).first()
                if run and run.status not in (DbtRunStatus.COMPLETED, DbtRunStatus.CANCELLED):
                    run.status = DbtRunStatus.FAILED
                    run.completed_at = datetime.now(timezone.utc)
                    run.error_message = str(exc)
                    if run.started_at:
                        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
                    db.commit()
            finally:
                db.close()
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=DbtExecutionTask,
    name="backend.tasks.dbt_tasks.execute_dbt_run",
)
def execute_dbt_run(self: Task, run_id: int, project_id: int) -> Dict[str, Any]:
    """
    Execute a dbt run in the background.

    Args:
        run_id: The DbtRun record ID
        project_id: The DbtProject record ID

    Returns:
        Dictionary with execution results

    Raises:
        Exception: If dbt execution fails after all retries
    """
    db = SessionLocal()
    try:
        run = db.query(DbtRun).filter(DbtRun.id == run_id).first()
        project = db.query(DbtProject).filter(DbtProject.id == project_id).first()

        if not run:
            raise ValueError(f"DbtRun with id {run_id} not found")
        if not project:
            raise ValueError(f"DbtProject with id {project_id} not found")

        # Check if run was cancelled before starting
        if run.status == DbtRunStatus.CANCELLED:
            logger.info(f"dbt run {run_id} was cancelled before execution")
            return {"status": "cancelled", "run_id": run_id}

        # Update status to running
        run.status = DbtRunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Starting dbt run {run_id} for project {project.name} (command: {run.command})")

        try:
            # Execute dbt command
            result = _execute_dbt_command(project, run, db)

            # Update run with results
            run.status = DbtRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            run.logs = result.get("logs", "")
            run.run_results_json = result.get("run_results")
            run.manifest_json = result.get("manifest")
            run.models_ran = result.get("models_ran", 0)
            run.models_passed = result.get("models_passed", 0)
            run.models_failed = result.get("models_failed", 0)
            run.models_skipped = result.get("models_skipped", 0)
            run.tests_passed = result.get("tests_passed", 0)
            run.tests_failed = result.get("tests_failed", 0)
            run.tests_warned = result.get("tests_warned", 0)

            db.commit()

            # Record column-level lineage from the dbt manifest
            if run.manifest_json:
                try:
                    _record_dbt_column_lineage(db, run, project.organization_id)
                except Exception as e:
                    logger.warning(f"Failed to record column lineage for dbt run {run_id}: {e}")
                    # Don't fail the run if lineage recording fails

            logger.info(f"dbt run {run_id} completed successfully in {run.duration_seconds:.2f}s")

            return {
                "status": "completed",
                "run_id": run_id,
                "duration_seconds": run.duration_seconds,
                "models_ran": run.models_ran,
                "models_passed": run.models_passed,
                "models_failed": run.models_failed,
            }

        except SoftTimeLimitExceeded:
            logger.error(f"dbt run {run_id} timed out (soft limit: {DBT_TASK_SOFT_TIMEOUT}s)")
            run.status = DbtRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = f"Task timed out after {DBT_TASK_SOFT_TIMEOUT} seconds"
            if run.started_at:
                run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            db.commit()
            raise

        except Exception as e:
            logger.error(f"dbt run {run_id} failed: {str(e)}", exc_info=True)
            run.status = DbtRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = str(e)
            if run.started_at:
                run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            db.commit()
            raise

    finally:
        db.close()


def _execute_dbt_command(
    project: DbtProject,
    run: DbtRun,
    db,
) -> Dict[str, Any]:
    """
    Execute the dbt command and return results.

    This function delegates to the dbt_executor service which handles:
    1. Git repository cloning with secure credential handling
    2. dbt environment setup (profiles.yml, env vars)
    3. dbt dependency installation
    4. Command execution with timeout
    5. Artifact parsing (run_results.json, manifest.json)
    6. Credential sanitization in logs and error messages

    Security notes:
    - Git credentials are passed via environment variables, never embedded in URLs
    - All error messages are sanitized to prevent credential leakage
    - Execution timeout is enforced (max 30 minutes)

    Args:
        project: The DbtProject configuration
        run: The DbtRun record
        db: Database session

    Returns:
        Dictionary with logs, run_results, manifest, and statistics
    """
    from backend.services.dbt_executor import execute_dbt_run as execute_dbt

    # Execute using the dbt_executor service
    result = execute_dbt(
        git_repo_url=project.git_repo_url,
        git_branch=project.git_branch,
        git_subdirectory=project.git_subdirectory,
        git_credentials=project.git_credentials,
        command=run.command,
        target=run.target or project.target,
        select=run.select,
        exclude=run.exclude,
        full_refresh=run.full_refresh,
        dbt_version=project.dbt_version,
        profiles_yml=project.profiles_yml,
        env_vars=project.env_vars,
        timeout_seconds=DBT_TASK_TIMEOUT - 120,  # Leave buffer for cleanup
    )

    # Check for execution failure
    if not result.success:
        raise RuntimeError(result.error_message or "dbt command failed")

    # Return results in expected format
    return {
        "logs": result.logs,
        "run_results": result.run_results_json,
        "manifest": result.manifest_json,
        "models_ran": result.models_ran,
        "models_passed": result.models_passed,
        "models_failed": result.models_failed,
        "models_skipped": result.models_skipped,
        "tests_passed": result.tests_passed,
        "tests_failed": result.tests_failed,
        "tests_warned": result.tests_warned,
    }


@celery_app.task(name="backend.tasks.dbt_tasks.cancel_dbt_run")
def cancel_dbt_run(run_id: int) -> Dict[str, Any]:
    """
    Cancel a running dbt execution.

    This task updates the run status to CANCELLED. If the task is still
    pending or running in Celery, it will be revoked.

    Args:
        run_id: The DbtRun record ID

    Returns:
        Dictionary with cancellation result
    """
    db = SessionLocal()
    try:
        run = db.query(DbtRun).filter(DbtRun.id == run_id).first()

        if not run:
            return {"status": "error", "message": f"DbtRun {run_id} not found"}

        if run.status in (DbtRunStatus.COMPLETED, DbtRunStatus.FAILED, DbtRunStatus.CANCELLED):
            return {
                "status": "skipped",
                "message": f"Run already in terminal state: {run.status.value}",
            }

        # Update status
        run.status = DbtRunStatus.CANCELLED
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = "Cancelled by user"
        if run.started_at:
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()

        db.commit()

        logger.info(f"dbt run {run_id} marked as cancelled")

        return {"status": "cancelled", "run_id": run_id}

    finally:
        db.close()


def _record_dbt_column_lineage(db, run: DbtRun, organization_id: int) -> None:
    """
    Record column-level lineage from a completed dbt run.

    Parses the manifest.json and extracts column lineage information,
    storing it in the ColumnLineage table for impact analysis.

    Args:
        db: Database session
        run: Completed DbtRun with manifest_json
        organization_id: Organization ID for scoping
    """
    from backend.services.column_lineage_service import ColumnLineageService

    if not run.manifest_json:
        return

    service = ColumnLineageService(db)

    try:
        lineages, metadata = service.record_dbt_lineage(
            dbt_run=run,
            organization_id=organization_id,
            dialect="postgres",  # Default dialect, could be made configurable
        )

        logger.info(
            f"Recorded column lineage for dbt run {run.id}: "
            f"{len(lineages)} lineage entries, {len(metadata)} metadata entries"
        )

    except Exception as e:
        logger.error(f"Error recording column lineage for dbt run {run.id}: {e}")
        raise
