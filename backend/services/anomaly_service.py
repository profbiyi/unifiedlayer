"""
Anomaly Detection Service.

Analyses PipelineRun history to detect data anomalies and fires alerts
via email and/or WhatsApp when unusual patterns are detected.

Detects four classes of anomaly:
    - row_drop        : Synced significantly fewer rows than 7-day rolling average.
    - failure_spike   : More than 3 failures for the same pipeline within 24 hours.
    - slow_sync       : Sync duration > 3× the rolling average.
    - zero_rows       : Pipeline completed successfully but synced 0 rows when
                        it normally syncs > 0.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.pipeline import Pipeline, PipelineRun, PipelineStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# How many recent runs (within 24 h) to inspect for "current" behaviour.
RECENT_WINDOW_HOURS: int = 24

# How many days of historical runs to use when computing the baseline average.
BASELINE_WINDOW_DAYS: int = 7

# Thresholds
ROW_DROP_RATIO: float = 0.50        # < 50 % of average → anomaly
SLOW_SYNC_MULTIPLIER: float = 3.0   # > 3× average duration → anomaly
FAILURE_SPIKE_THRESHOLD: int = 3    # > 3 failures in 24 h → anomaly

# Minimum baseline runs before we consider a comparison meaningful.
MIN_BASELINE_RUNS: int = 3


# ---------------------------------------------------------------------------
# Data class for anomaly alerts
# ---------------------------------------------------------------------------

@dataclass
class AnomalyAlert:
    """Represents a detected anomaly for a pipeline."""

    pipeline_id: int
    pipeline_name: str
    org_id: int
    alert_type: str   # "row_drop" | "failure_spike" | "slow_sync" | "zero_rows"
    severity: str     # "warning" | "critical"
    message: str
    details: Dict = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        """Unique key used for alert deduplication."""
        return f"{self.pipeline_id}:{self.alert_type}"

    def __repr__(self) -> str:
        return (
            f"<AnomalyAlert pipeline_id={self.pipeline_id} "
            f"type={self.alert_type} severity={self.severity}>"
        )


# ---------------------------------------------------------------------------
# AnomalyDetector
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """
    Checks pipeline run history for anomalies.

    Usage::

        with SessionLocal() as db:
            detector = AnomalyDetector(db)
            alerts = detector.check_all_pipelines()
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check_all_pipelines(self) -> List[AnomalyAlert]:
        """
        Check every active pipeline for anomalies.

        Returns:
            Flat list of AnomalyAlert objects (may be empty).
        """
        pipelines: List[Pipeline] = (
            self.db.query(Pipeline).filter(Pipeline.is_active.is_(True)).all()
        )

        all_alerts: List[AnomalyAlert] = []
        for pipeline in pipelines:
            try:
                alerts = self._check_pipeline_internal(pipeline)
                all_alerts.extend(alerts)
            except Exception:
                logger.exception(
                    "Anomaly check failed for pipeline id=%s name=%s",
                    pipeline.id,
                    pipeline.name,
                )

        logger.info(
            "Anomaly check complete: %d pipelines checked, %d anomalies found.",
            len(pipelines),
            len(all_alerts),
        )
        return all_alerts

    def check_pipeline(self, pipeline_id: int) -> List[AnomalyAlert]:
        """
        Check a specific pipeline for anomalies.

        Args:
            pipeline_id: Primary key of the pipeline.

        Returns:
            List of AnomalyAlert objects (may be empty).

        Raises:
            ValueError: If the pipeline is not found.
        """
        pipeline: Optional[Pipeline] = (
            self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        )
        if pipeline is None:
            raise ValueError(f"Pipeline id={pipeline_id} not found.")

        return self._check_pipeline_internal(pipeline)

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------

    def _check_pipeline_internal(self, pipeline: Pipeline) -> List[AnomalyAlert]:
        """Run all anomaly checks for a single pipeline."""
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=RECENT_WINDOW_HOURS)
        baseline_cutoff = now - timedelta(days=BASELINE_WINDOW_DAYS)

        # Runs in the last 24 hours (used for current-state checks).
        recent_runs: List[PipelineRun] = (
            self.db.query(PipelineRun)
            .filter(
                PipelineRun.pipeline_id == pipeline.id,
                PipelineRun.created_at >= recent_cutoff,
            )
            .order_by(PipelineRun.created_at.desc())
            .all()
        )

        # Runs in the 7-day baseline window (used for rolling averages).
        # Exclude the last 24 hours so the baseline is not contaminated by
        # the very events we are trying to detect.
        baseline_runs: List[PipelineRun] = (
            self.db.query(PipelineRun)
            .filter(
                PipelineRun.pipeline_id == pipeline.id,
                PipelineRun.created_at >= baseline_cutoff,
                PipelineRun.created_at < recent_cutoff,
                PipelineRun.status == PipelineStatus.COMPLETED,
            )
            .order_by(PipelineRun.created_at.desc())
            .all()
        )

        alerts: List[AnomalyAlert] = []

        for check_fn in (
            self._check_row_count,
            self._check_failure_spike,
            self._check_sync_duration,
            self._check_zero_rows,
        ):
            try:
                alert = check_fn(pipeline, recent_runs, baseline_runs)
                if alert is not None:
                    alerts.append(alert)
            except Exception:
                logger.exception(
                    "Check %s failed for pipeline id=%s",
                    check_fn.__name__,
                    pipeline.id,
                )

        return alerts

    # ------------------------------------------------------------------
    # Individual anomaly checks
    # ------------------------------------------------------------------

    def _check_row_count(
        self,
        pipeline: Pipeline,
        recent_runs: List[PipelineRun],
        baseline_runs: List[PipelineRun],
    ) -> Optional[AnomalyAlert]:
        """
        Row-count anomaly: the most recent completed run synced < 50 % of the
        rolling 7-day average row count.
        """
        if len(baseline_runs) < MIN_BASELINE_RUNS:
            return None

        # Baseline: average rows_written across historical completed runs.
        baseline_rows = [
            r.rows_written
            for r in baseline_runs
            if r.rows_written is not None and r.rows_written > 0
        ]
        if not baseline_rows:
            return None

        avg_rows = sum(baseline_rows) / len(baseline_rows)
        if avg_rows == 0:
            return None

        # Most recent *completed* run in the recent window.
        recent_completed = [
            r for r in recent_runs if r.status == PipelineStatus.COMPLETED
        ]
        if not recent_completed:
            return None

        latest_run = recent_completed[0]
        latest_rows = latest_run.rows_written or 0

        if latest_rows < avg_rows * ROW_DROP_RATIO:
            drop_pct = round((1 - latest_rows / avg_rows) * 100, 1)
            return AnomalyAlert(
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                org_id=pipeline.organization_id,
                alert_type="row_drop",
                severity="warning",
                message=(
                    f"Data volume drop detected for pipeline '{pipeline.name}': "
                    f"synced {latest_rows:,} rows (7-day avg: {avg_rows:,.0f}, "
                    f"drop: {drop_pct}%)"
                ),
                details={
                    "latest_rows": latest_rows,
                    "avg_rows": avg_rows,
                    "drop_pct": drop_pct,
                    "run_id": latest_run.id,
                    "baseline_sample_size": len(baseline_rows),
                },
            )
        return None

    def _check_failure_spike(
        self,
        pipeline: Pipeline,
        recent_runs: List[PipelineRun],
        baseline_runs: List[PipelineRun],  # unused — kept for uniform signature
    ) -> Optional[AnomalyAlert]:
        """
        Failure-spike anomaly: more than 3 failed runs in the last 24 hours.
        """
        failed_runs = [
            r for r in recent_runs if r.status == PipelineStatus.FAILED
        ]
        failure_count = len(failed_runs)

        if failure_count > FAILURE_SPIKE_THRESHOLD:
            return AnomalyAlert(
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                org_id=pipeline.organization_id,
                alert_type="failure_spike",
                severity="critical",
                message=(
                    f"Repeated pipeline failures for '{pipeline.name}': "
                    f"{failure_count} failures in the last 24 hours"
                ),
                details={
                    "failure_count": failure_count,
                    "threshold": FAILURE_SPIKE_THRESHOLD,
                    "run_ids": [r.id for r in failed_runs],
                    "latest_error": (
                        failed_runs[0].error_message or "No error message recorded"
                    ),
                },
            )
        return None

    def _check_sync_duration(
        self,
        pipeline: Pipeline,
        recent_runs: List[PipelineRun],
        baseline_runs: List[PipelineRun],
    ) -> Optional[AnomalyAlert]:
        """
        Slow-sync anomaly: most recent completed run took > 3× the rolling
        average duration.
        """
        if len(baseline_runs) < MIN_BASELINE_RUNS:
            return None

        # Use the stored duration_seconds field; fall back to computing from
        # started_at / completed_at when it is not populated.
        def _duration(run: PipelineRun) -> Optional[float]:
            if run.duration_seconds is not None:
                return run.duration_seconds
            if run.started_at and run.completed_at:
                # Ensure both datetimes are timezone-aware before subtracting.
                started = run.started_at
                completed = run.completed_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=timezone.utc)
                delta = (completed - started).total_seconds()
                return delta if delta > 0 else None
            return None

        baseline_durations = [
            d for r in baseline_runs if (d := _duration(r)) is not None and d > 0
        ]
        if not baseline_durations:
            return None

        avg_duration = sum(baseline_durations) / len(baseline_durations)
        if avg_duration == 0:
            return None

        recent_completed = [
            r for r in recent_runs if r.status == PipelineStatus.COMPLETED
        ]
        if not recent_completed:
            return None

        latest_run = recent_completed[0]
        latest_duration = _duration(latest_run)
        if latest_duration is None:
            return None

        if latest_duration > avg_duration * SLOW_SYNC_MULTIPLIER:
            ratio = round(latest_duration / avg_duration, 1)
            return AnomalyAlert(
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                org_id=pipeline.organization_id,
                alert_type="slow_sync",
                severity="warning",
                message=(
                    f"Sync taking longer than usual for '{pipeline.name}': "
                    f"{latest_duration:.0f}s (7-day avg: {avg_duration:.0f}s, "
                    f"{ratio}× slower)"
                ),
                details={
                    "latest_duration_seconds": latest_duration,
                    "avg_duration_seconds": avg_duration,
                    "ratio": ratio,
                    "run_id": latest_run.id,
                    "baseline_sample_size": len(baseline_durations),
                },
            )
        return None

    def _check_zero_rows(
        self,
        pipeline: Pipeline,
        recent_runs: List[PipelineRun],
        baseline_runs: List[PipelineRun],
    ) -> Optional[AnomalyAlert]:
        """
        Zero-rows anomaly: pipeline completed successfully but synced 0 rows
        when it normally syncs > 0.
        """
        if len(baseline_runs) < MIN_BASELINE_RUNS:
            return None

        # Only flag if the pipeline *normally* syncs at least some rows.
        baseline_with_rows = [
            r
            for r in baseline_runs
            if r.rows_written is not None and r.rows_written > 0
        ]
        if len(baseline_with_rows) < MIN_BASELINE_RUNS:
            # Pipeline has a history of syncing 0 rows — not anomalous.
            return None

        # Most recent completed run in the last 24 hours.
        recent_completed = [
            r for r in recent_runs if r.status == PipelineStatus.COMPLETED
        ]
        if not recent_completed:
            return None

        latest_run = recent_completed[0]
        latest_rows = latest_run.rows_written

        if latest_rows is not None and latest_rows == 0:
            avg_rows = sum(
                r.rows_written for r in baseline_with_rows
            ) / len(baseline_with_rows)
            return AnomalyAlert(
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                org_id=pipeline.organization_id,
                alert_type="zero_rows",
                severity="warning",
                message=(
                    f"No data synced for '{pipeline.name}': "
                    f"pipeline completed successfully but wrote 0 rows "
                    f"(7-day avg: {avg_rows:,.0f} rows)"
                ),
                details={
                    "run_id": latest_run.id,
                    "rows_written": 0,
                    "avg_rows": avg_rows,
                    "baseline_sample_size": len(baseline_with_rows),
                },
            )
        return None
