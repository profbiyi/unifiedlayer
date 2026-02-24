"""
Pipeline Retry Handler Service.

Handles automatic retries for failed pipeline runs with:
- Exponential backoff with jitter (prevents thundering herd)
- Non-blocking scheduling (doesn't block the main process)
- Configurable retry policies
"""

import logging
import random
import threading
from typing import Optional
from datetime import datetime, timezone, timedelta

from backend.database import get_db_session
from backend.models import Pipeline, PipelineRun
from backend.models.pipeline import PipelineStatus

logger = logging.getLogger(__name__)

# Track active retry timers to allow cancellation if needed
_active_timers: dict = {}


def calculate_retry_delay(
    base_delay: int,
    retry_count: int,
    exponential_backoff: bool = False,
    max_delay: int = 3600,
    jitter: bool = True,
    jitter_factor: float = 0.25,
) -> float:
    """
    Calculate retry delay in seconds with optional jitter.

    Jitter adds randomness to prevent multiple failed pipelines from
    retrying simultaneously (thundering herd problem).

    Args:
        base_delay: Base delay in seconds
        retry_count: Current retry attempt (0-indexed)
        exponential_backoff: Whether to use exponential backoff
        max_delay: Maximum delay in seconds (default: 1 hour)
        jitter: Whether to add random jitter
        jitter_factor: Jitter range as fraction of delay (0.25 = +/- 25%)

    Returns:
        Delay in seconds (float to account for jitter)
    """
    if exponential_backoff:
        # Exponential backoff: delay = base_delay * (2 ** retry_count)
        delay = base_delay * (2 ** retry_count)
    else:
        delay = base_delay

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter to prevent thundering herd
    if jitter and delay > 0:
        # Add random jitter: delay * (1 +/- jitter_factor)
        # e.g., with jitter_factor=0.25, a 60s delay becomes 45-75s
        jitter_range = delay * jitter_factor
        delay = delay + random.uniform(-jitter_range, jitter_range)
        # Ensure delay is still positive
        delay = max(1.0, delay)

    return delay


def should_retry_pipeline(pipeline: Pipeline, run: PipelineRun) -> bool:
    """
    Determine if a failed pipeline run should be retried.

    Args:
        pipeline: Pipeline configuration
        run: Failed pipeline run

    Returns:
        True if should retry, False otherwise
    """
    # Check if retries are configured
    if not hasattr(pipeline, 'max_retries') or pipeline.max_retries <= 0:
        logger.info(f"No retries configured for pipeline {pipeline.id}")
        return False

    # Check if we've exhausted retry attempts
    current_retry = run.retry_count if run.retry_count else 0
    if current_retry >= pipeline.max_retries:
        logger.info(
            f"Max retries ({pipeline.max_retries}) reached for pipeline {pipeline.id}, "
            f"run {run.id} (retry_count={current_retry})"
        )
        return False

    # Only retry if pipeline is active
    if not pipeline.is_active:
        logger.info(f"Pipeline {pipeline.id} is not active, skipping retry")
        return False

    logger.info(
        f"Pipeline {pipeline.id} run {run.id} will be retried "
        f"(attempt {current_retry + 1}/{pipeline.max_retries})"
    )
    return True


def _execute_delayed_retry(pipeline_id: int, run_id: int) -> None:
    """
    Execute a retry after the delay has elapsed.
    This runs in a background thread.

    Args:
        pipeline_id: Pipeline ID
        run_id: Retry run ID
    """
    # Clean up timer reference
    timer_key = f"{pipeline_id}:{run_id}"
    _active_timers.pop(timer_key, None)

    db = get_db_session()
    try:
        # Verify the run still exists and is pending
        retry_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not retry_run:
            logger.warning(f"Retry run {run_id} not found, skipping")
            return

        if retry_run.status != PipelineStatus.PENDING:
            logger.info(f"Retry run {run_id} is no longer pending (status={retry_run.status}), skipping")
            return

        # Verify pipeline is still active
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline or not pipeline.is_active:
            logger.info(f"Pipeline {pipeline_id} is not active, cancelling retry")
            retry_run.status = PipelineStatus.CANCELLED
            retry_run.error_message = "Pipeline deactivated before retry"
            db.commit()
            return

        # Trigger the retry run
        logger.info(f"Triggering delayed retry run {run_id} for pipeline {pipeline_id}")

        try:
            from backend.prefect_flows.pipeline_flow import execute_pipeline_flow

            # Use Prefect's async submission
            execute_pipeline_flow.delay(pipeline_id=pipeline_id, run_id=run_id)
            logger.info(f"Successfully triggered retry run {run_id}")

        except Exception as e:
            logger.error(f"Failed to trigger retry run {run_id}: {str(e)}", exc_info=True)
            retry_run.status = PipelineStatus.FAILED
            retry_run.error_message = f"Failed to trigger retry: {str(e)}"
            db.commit()

    except Exception as e:
        logger.error(f"Error in delayed retry execution: {str(e)}", exc_info=True)
    finally:
        db.close()


def schedule_pipeline_retry(
    pipeline_id: int,
    failed_run_id: int,
    retry_immediately: bool = False,
) -> Optional[int]:
    """
    Schedule a retry for a failed pipeline run using non-blocking timers.

    This function returns immediately after scheduling. The actual retry
    execution happens asynchronously after the calculated delay.

    Args:
        pipeline_id: Pipeline ID
        failed_run_id: ID of the failed run
        retry_immediately: If True, trigger retry immediately (for testing)

    Returns:
        ID of the new retry run, or None if retry not scheduled
    """
    db = get_db_session()
    try:
        # Get pipeline and failed run
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            logger.error(f"Pipeline {pipeline_id} not found")
            return None

        failed_run = db.query(PipelineRun).filter(PipelineRun.id == failed_run_id).first()
        if not failed_run:
            logger.error(f"Pipeline run {failed_run_id} not found")
            return None

        # Check if should retry
        if not should_retry_pipeline(pipeline, failed_run):
            return None

        # Calculate retry delay with jitter
        current_retry = failed_run.retry_count if failed_run.retry_count else 0
        retry_count = current_retry + 1

        base_delay = getattr(pipeline, 'retry_delay_seconds', 60)
        exp_backoff = getattr(pipeline, 'exponential_backoff_enabled', False)

        delay_seconds = calculate_retry_delay(
            base_delay=base_delay,
            retry_count=retry_count,
            exponential_backoff=exp_backoff,
            jitter=True,  # Always use jitter to prevent thundering herd
        )

        # Calculate scheduled execution time
        scheduled_for = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

        logger.info(
            f"Scheduling retry for pipeline {pipeline_id} at {scheduled_for.isoformat()} "
            f"(delay: {delay_seconds:.1f}s, retry {retry_count}/{pipeline.max_retries})"
        )

        # Get original run ID (if this is already a retry, use its original_run_id)
        original_run_id = failed_run.original_run_id if failed_run.is_retry else failed_run.id

        # Create new retry run with scheduled time in metadata
        retry_run = PipelineRun(
            pipeline_id=pipeline_id,
            status=PipelineStatus.PENDING,
            retry_count=retry_count,
            is_retry=True,
            original_run_id=original_run_id,
            run_metadata={
                "retry_reason": "automatic_retry",
                "failed_run_id": failed_run_id,
                "retry_delay_seconds": round(delay_seconds, 2),
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
                "scheduled_for": scheduled_for.isoformat(),
            },
        )

        db.add(retry_run)
        db.commit()
        db.refresh(retry_run)

        logger.info(f"Created retry run {retry_run.id} for pipeline {pipeline_id}")

        # Schedule the retry execution (non-blocking)
        if retry_immediately:
            # For testing: execute immediately in background thread
            delay_seconds = 0

        # Use threading.Timer for non-blocking delayed execution
        timer_key = f"{pipeline_id}:{retry_run.id}"
        timer = threading.Timer(
            delay_seconds,
            _execute_delayed_retry,
            args=(pipeline_id, retry_run.id)
        )
        timer.daemon = True  # Don't prevent process shutdown
        timer.start()

        # Track timer for potential cancellation
        _active_timers[timer_key] = timer

        logger.info(f"Scheduled retry run {retry_run.id} to execute in {delay_seconds:.1f} seconds")
        return retry_run.id

    except Exception as e:
        logger.error(f"Failed to schedule pipeline retry: {str(e)}", exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


def cancel_pending_retry(pipeline_id: int, run_id: int) -> bool:
    """
    Cancel a pending retry that hasn't executed yet.

    Args:
        pipeline_id: Pipeline ID
        run_id: Retry run ID to cancel

    Returns:
        True if cancelled, False if not found or already executed
    """
    timer_key = f"{pipeline_id}:{run_id}"
    timer = _active_timers.pop(timer_key, None)

    if timer:
        timer.cancel()
        logger.info(f"Cancelled pending retry timer for run {run_id}")

        # Update run status
        db = get_db_session()
        try:
            run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if run and run.status == PipelineStatus.PENDING:
                run.status = PipelineStatus.CANCELLED
                run.error_message = "Retry cancelled"
                db.commit()
        finally:
            db.close()

        return True

    return False


def get_pending_retries() -> list:
    """
    Get list of pending retry run IDs.

    Returns:
        List of (pipeline_id, run_id) tuples
    """
    return [(int(k.split(':')[0]), int(k.split(':')[1])) for k in _active_timers.keys()]


def handle_pipeline_failure(
    pipeline_id: int,
    run_id: int,
    error_message: str,
    retry_immediately: bool = False,
) -> Optional[int]:
    """
    Handle a pipeline failure and potentially schedule a retry.

    This is the main entry point for retry logic after a pipeline fails.
    Returns immediately after scheduling the retry (non-blocking).

    Args:
        pipeline_id: Pipeline ID
        run_id: Failed run ID
        error_message: Error message from failure
        retry_immediately: If True, trigger retry immediately (for testing)

    Returns:
        ID of retry run if scheduled, None otherwise
    """
    logger.info(
        f"Handling pipeline failure: pipeline_id={pipeline_id}, "
        f"run_id={run_id}, error={error_message[:100]}..."
    )

    return schedule_pipeline_retry(
        pipeline_id=pipeline_id,
        failed_run_id=run_id,
        retry_immediately=retry_immediately,
    )
