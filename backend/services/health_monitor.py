"""
Health Monitoring Service.

Provides health check functions for sources, pipelines, and destinations.
Calculates health scores and detects issues proactively.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.models.pipeline import (
    DataSource,
    Pipeline,
    PipelineRun,
    PipelineStatus,
    Destination,
)
from backend.models.health import (
    ResourceHealth,
    HealthCheckLog,
    HealthStatus,
    ResourceType,
)
from backend.utils.connection_tester import test_connection, test_destination_connection

logger = logging.getLogger(__name__)


# Issue codes
class IssueCodes:
    """Standard issue codes for health problems."""
    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    TOKEN_EXPIRING = "TOKEN_EXPIRING"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    HIGH_FAILURE_RATE = "HIGH_FAILURE_RATE"
    NO_RECENT_RUNS = "NO_RECENT_RUNS"
    STALE_SYNC = "STALE_SYNC"
    CONSECUTIVE_FAILURES = "CONSECUTIVE_FAILURES"
    SLOW_EXECUTION = "SLOW_EXECUTION"
    NO_RUNS_EVER = "NO_RUNS_EVER"
    INACTIVE = "INACTIVE"


def calculate_health_score(issues: List[Dict[str, Any]]) -> Tuple[float, HealthStatus]:
    """
    Calculate health score based on detected issues.

    Args:
        issues: List of issue dictionaries with severity

    Returns:
        Tuple of (score 0-100, status)
    """
    if not issues:
        return 100.0, HealthStatus.HEALTHY

    # Count issues by severity
    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    warning_count = sum(1 for i in issues if i.get("severity") == "warning")
    info_count = sum(1 for i in issues if i.get("severity") == "info")

    # Calculate score deductions
    # Critical issues: -30 each (capped at -90)
    # Warning issues: -15 each (capped at -45)
    # Info issues: -5 each (capped at -15)
    critical_deduction = min(critical_count * 30, 90)
    warning_deduction = min(warning_count * 15, 45)
    info_deduction = min(info_count * 5, 15)

    score = max(0.0, 100.0 - critical_deduction - warning_deduction - info_deduction)

    # Determine status
    if critical_count > 0 or score < 30:
        status = HealthStatus.CRITICAL
    elif warning_count > 0 or score < 70:
        status = HealthStatus.WARNING
    else:
        status = HealthStatus.HEALTHY

    return score, status


def check_source_connectivity(
    source: DataSource,
    db: Session,
) -> Dict[str, Any]:
    """
    Test source connection and return health metrics.

    Args:
        source: DataSource model instance
        db: Database session

    Returns:
        Dict with connection test results
    """
    start_time = datetime.now(timezone.utc)

    try:
        source_type = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)
        success, message = test_connection(source_type.lower(), source.config or {})

        end_time = datetime.now(timezone.utc)
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "success": success,
            "message": message,
            "latency_ms": latency_ms,
            "error": None if success else message,
            "checked_at": end_time.isoformat(),
        }
    except Exception as e:
        logger.error(f"Connection test failed for source {source.id}: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "latency_ms": None,
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def check_oauth_token_expiry(source: DataSource) -> Dict[str, Any]:
    """
    Check if OAuth tokens are expiring soon.

    Args:
        source: DataSource model instance

    Returns:
        Dict with token expiry information
    """
    config = source.config or {}

    # Check for common OAuth token expiry fields
    expiry_fields = [
        "token_expires_at",
        "access_token_expires_at",
        "oauth_token_expires_at",
        "expires_at",
    ]

    expires_at = None
    for field in expiry_fields:
        if field in config:
            try:
                expires_at = datetime.fromisoformat(config[field].replace('Z', '+00:00'))
                break
            except (ValueError, TypeError):
                pass

    if expires_at is None:
        return {
            "has_oauth": False,
            "expires_at": None,
            "days_until_expiry": None,
            "warning": False,
            "expired": False,
        }

    now = datetime.now(timezone.utc)
    days_until_expiry = (expires_at - now).days

    return {
        "has_oauth": True,
        "expires_at": expires_at.isoformat(),
        "days_until_expiry": days_until_expiry,
        "warning": 0 < days_until_expiry <= 7,  # Warn if expiring within 7 days
        "expired": days_until_expiry <= 0,
    }


def check_pipeline_success_rate(
    pipeline: Pipeline,
    db: Session,
    num_runs: int = 10,
) -> Dict[str, Any]:
    """
    Calculate pipeline success rate from recent runs.

    Args:
        pipeline: Pipeline model instance
        db: Database session
        num_runs: Number of recent runs to consider

    Returns:
        Dict with success rate metrics
    """
    # Get recent runs
    recent_runs = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline.id,
        PipelineRun.status.in_([PipelineStatus.COMPLETED, PipelineStatus.FAILED]),
    ).order_by(PipelineRun.created_at.desc()).limit(num_runs).all()

    if not recent_runs:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": None,
            "has_data": False,
        }

    successful = sum(1 for r in recent_runs if r.status == PipelineStatus.COMPLETED)
    failed = sum(1 for r in recent_runs if r.status == PipelineStatus.FAILED)
    total = len(recent_runs)

    return {
        "total_runs": total,
        "successful_runs": successful,
        "failed_runs": failed,
        "success_rate": successful / total if total > 0 else 0.0,
        "has_data": True,
    }


def check_sync_freshness(
    pipeline: Pipeline,
    db: Session,
    stale_hours: int = 48,
) -> Dict[str, Any]:
    """
    Check time since last successful sync.

    Args:
        pipeline: Pipeline model instance
        db: Database session
        stale_hours: Hours after which sync is considered stale

    Returns:
        Dict with sync freshness metrics
    """
    # Get last successful run
    last_success = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline.id,
        PipelineRun.status == PipelineStatus.COMPLETED,
    ).order_by(PipelineRun.completed_at.desc()).first()

    if not last_success or not last_success.completed_at:
        # Check if there are any runs at all
        any_run = db.query(PipelineRun).filter(
            PipelineRun.pipeline_id == pipeline.id,
        ).first()

        return {
            "last_successful_sync": None,
            "hours_since_sync": None,
            "is_stale": any_run is not None,  # Stale if runs exist but none succeeded
            "has_ever_synced": False,
            "threshold_hours": stale_hours,
        }

    now = datetime.now(timezone.utc)
    last_sync = last_success.completed_at
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)

    hours_since = (now - last_sync).total_seconds() / 3600

    return {
        "last_successful_sync": last_sync.isoformat(),
        "hours_since_sync": round(hours_since, 2),
        "is_stale": hours_since > stale_hours,
        "has_ever_synced": True,
        "threshold_hours": stale_hours,
    }


def check_consecutive_failures(
    pipeline: Pipeline,
    db: Session,
    threshold: int = 3,
) -> Dict[str, Any]:
    """
    Check for consecutive failures in pipeline runs.

    Args:
        pipeline: Pipeline model instance
        db: Database session
        threshold: Number of consecutive failures to trigger warning

    Returns:
        Dict with consecutive failure metrics
    """
    # Get most recent runs
    recent_runs = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline.id,
        PipelineRun.status.in_([PipelineStatus.COMPLETED, PipelineStatus.FAILED]),
    ).order_by(PipelineRun.created_at.desc()).limit(threshold + 2).all()

    if not recent_runs:
        return {
            "consecutive_failures": 0,
            "threshold": threshold,
            "is_concerning": False,
        }

    # Count consecutive failures from most recent
    consecutive = 0
    for run in recent_runs:
        if run.status == PipelineStatus.FAILED:
            consecutive += 1
        else:
            break

    return {
        "consecutive_failures": consecutive,
        "threshold": threshold,
        "is_concerning": consecutive >= threshold,
    }


def get_source_health(
    source: DataSource,
    db: Session,
    run_connection_test: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive health status for a source.

    Args:
        source: DataSource model instance
        db: Database session
        run_connection_test: Whether to test the actual connection

    Returns:
        Dict with full health assessment
    """
    issues = []
    metrics = {}

    # Check if source is active
    if not source.is_active:
        issues.append({
            "code": IssueCodes.INACTIVE,
            "message": "Source is inactive",
            "severity": "info",
        })

    # Check connectivity (if enabled)
    if run_connection_test and source.is_active:
        conn_result = check_source_connectivity(source, db)
        metrics["connection_test"] = conn_result

        if not conn_result["success"]:
            severity = "critical"
            if "timeout" in (conn_result.get("error") or "").lower():
                issues.append({
                    "code": IssueCodes.CONNECTION_TIMEOUT,
                    "message": f"Connection timed out: {conn_result.get('error', 'Unknown error')}",
                    "severity": severity,
                })
            else:
                issues.append({
                    "code": IssueCodes.CONNECTION_FAILED,
                    "message": f"Connection failed: {conn_result.get('error', 'Unknown error')}",
                    "severity": severity,
                })

    # Check OAuth token expiry
    token_result = check_oauth_token_expiry(source)
    if token_result["has_oauth"]:
        metrics["token_expiry"] = token_result

        if token_result["expired"]:
            issues.append({
                "code": IssueCodes.TOKEN_EXPIRED,
                "message": "OAuth token has expired",
                "severity": "critical",
            })
        elif token_result["warning"]:
            issues.append({
                "code": IssueCodes.TOKEN_EXPIRING,
                "message": f"OAuth token expires in {token_result['days_until_expiry']} days",
                "severity": "warning",
            })

    # Calculate overall health
    score, status = calculate_health_score(issues)

    return {
        "resource_type": ResourceType.SOURCE,
        "resource_id": source.id,
        "status": status,
        "score": score,
        "issues": issues,
        "metrics": metrics,
        "checked_at": datetime.now(timezone.utc),
    }


def get_pipeline_health(
    pipeline: Pipeline,
    db: Session,
) -> Dict[str, Any]:
    """
    Get comprehensive health status for a pipeline.

    Args:
        pipeline: Pipeline model instance
        db: Database session

    Returns:
        Dict with full health assessment
    """
    issues = []
    metrics = {}

    # Check if pipeline is active
    if not pipeline.is_active:
        issues.append({
            "code": IssueCodes.INACTIVE,
            "message": "Pipeline is inactive",
            "severity": "info",
        })

    # Check success rate
    success_result = check_pipeline_success_rate(pipeline, db)
    metrics["success_rate"] = success_result

    if success_result["has_data"]:
        rate = success_result["success_rate"]
        if rate is not None and rate < 0.5:
            issues.append({
                "code": IssueCodes.HIGH_FAILURE_RATE,
                "message": f"High failure rate: {(1-rate)*100:.0f}% of recent runs failed",
                "severity": "critical" if rate < 0.3 else "warning",
            })

    # Check sync freshness
    freshness_result = check_sync_freshness(pipeline, db)
    metrics["sync_freshness"] = freshness_result

    if not freshness_result["has_ever_synced"]:
        # Check if pipeline has any runs at all
        any_run = db.query(PipelineRun).filter(
            PipelineRun.pipeline_id == pipeline.id
        ).first()

        if any_run:
            issues.append({
                "code": IssueCodes.NO_RECENT_RUNS,
                "message": "Pipeline has runs but none have completed successfully",
                "severity": "warning",
            })
        else:
            issues.append({
                "code": IssueCodes.NO_RUNS_EVER,
                "message": "Pipeline has never been run",
                "severity": "info",
            })
    elif freshness_result["is_stale"]:
        hours = freshness_result["hours_since_sync"]
        issues.append({
            "code": IssueCodes.STALE_SYNC,
            "message": f"No successful sync in {hours:.0f} hours",
            "severity": "warning" if hours < 96 else "critical",
        })

    # Check consecutive failures
    failures_result = check_consecutive_failures(pipeline, db)
    metrics["consecutive_failures"] = failures_result

    if failures_result["is_concerning"]:
        issues.append({
            "code": IssueCodes.CONSECUTIVE_FAILURES,
            "message": f"{failures_result['consecutive_failures']} consecutive failures",
            "severity": "critical",
        })

    # Calculate overall health
    score, status = calculate_health_score(issues)

    return {
        "resource_type": ResourceType.PIPELINE,
        "resource_id": pipeline.id,
        "status": status,
        "score": score,
        "issues": issues,
        "metrics": metrics,
        "checked_at": datetime.now(timezone.utc),
    }


def get_destination_health(
    destination: Destination,
    db: Session,
    run_connection_test: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive health status for a destination.

    Args:
        destination: Destination model instance
        db: Database session
        run_connection_test: Whether to test the actual connection

    Returns:
        Dict with full health assessment
    """
    issues = []
    metrics = {}

    # Check if destination is active
    if not destination.is_active:
        issues.append({
            "code": IssueCodes.INACTIVE,
            "message": "Destination is inactive",
            "severity": "info",
        })

    # Check connectivity (if enabled)
    if run_connection_test and destination.is_active:
        start_time = datetime.now(timezone.utc)
        try:
            dest_type = destination.destination_type.value if hasattr(destination.destination_type, 'value') else str(destination.destination_type)
            success, message = test_destination_connection(dest_type.lower(), destination.config or {})

            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)

            conn_result = {
                "success": success,
                "message": message,
                "latency_ms": latency_ms,
                "error": None if success else message,
                "checked_at": end_time.isoformat(),
            }
        except Exception as e:
            logger.error(f"Connection test failed for destination {destination.id}: {str(e)}")
            conn_result = {
                "success": False,
                "message": str(e),
                "latency_ms": None,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        metrics["connection_test"] = conn_result

        if not conn_result["success"]:
            severity = "critical"
            if "timeout" in (conn_result.get("error") or "").lower():
                issues.append({
                    "code": IssueCodes.CONNECTION_TIMEOUT,
                    "message": f"Connection timed out: {conn_result.get('error', 'Unknown error')}",
                    "severity": severity,
                })
            else:
                issues.append({
                    "code": IssueCodes.CONNECTION_FAILED,
                    "message": f"Connection failed: {conn_result.get('error', 'Unknown error')}",
                    "severity": severity,
                })

    # Calculate overall health
    score, status = calculate_health_score(issues)

    return {
        "resource_type": ResourceType.DESTINATION,
        "resource_id": destination.id,
        "status": status,
        "score": score,
        "issues": issues,
        "metrics": metrics,
        "checked_at": datetime.now(timezone.utc),
    }


def save_health_status(
    db: Session,
    organization_id: int,
    health_data: Dict[str, Any],
    check_type: str = "scheduled",
) -> ResourceHealth:
    """
    Save health status to database.

    Args:
        db: Database session
        organization_id: Organization ID
        health_data: Health assessment data from get_*_health functions
        check_type: Type of health check (scheduled, manual, on_demand)

    Returns:
        Updated ResourceHealth model
    """
    resource_type = health_data["resource_type"]
    resource_id = health_data["resource_id"]

    # Find or create health record
    health = db.query(ResourceHealth).filter(
        ResourceHealth.organization_id == organization_id,
        ResourceHealth.resource_type == resource_type,
        ResourceHealth.resource_id == resource_id,
    ).first()

    if not health:
        health = ResourceHealth(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.add(health)

    # Update health record
    health.status = health_data["status"]
    health.score = health_data["score"]
    health.issues = health_data["issues"]
    health.metrics = health_data["metrics"]
    health.last_checked_at = health_data["checked_at"]
    health.next_check_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    # Create log entry
    log_entry = HealthCheckLog(
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=health_data["status"],
        score=health_data["score"],
        issues=health_data["issues"],
        metrics=health_data["metrics"],
        check_type=check_type,
        checked_at=health_data["checked_at"],
    )
    db.add(log_entry)

    db.commit()
    db.refresh(health)

    return health


def get_organization_health_overview(
    db: Session,
    organization_id: int,
) -> Dict[str, Any]:
    """
    Get overall health overview for an organization.

    Args:
        db: Database session
        organization_id: Organization ID

    Returns:
        Dict with organization health summary
    """
    # Get all health records
    health_records = db.query(ResourceHealth).filter(
        ResourceHealth.organization_id == organization_id,
    ).all()

    # Count by status and type
    summary = {
        "total_resources": len(health_records),
        "healthy": 0,
        "warning": 0,
        "critical": 0,
        "unknown": 0,
        "by_type": {
            "source": {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0, "total": 0},
            "pipeline": {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0, "total": 0},
            "destination": {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0, "total": 0},
        },
        "average_score": 0.0,
        "critical_issues": [],
    }

    if not health_records:
        return summary

    total_score = 0.0
    for record in health_records:
        status_key = record.status.value if record.status else "unknown"
        type_key = record.resource_type.value if record.resource_type else "source"

        summary[status_key] += 1
        summary["by_type"][type_key][status_key] += 1
        summary["by_type"][type_key]["total"] += 1
        total_score += record.score

        # Collect critical issues
        if record.status == HealthStatus.CRITICAL:
            for issue in (record.issues or []):
                if issue.get("severity") == "critical":
                    summary["critical_issues"].append({
                        "resource_type": type_key,
                        "resource_id": record.resource_id,
                        "issue": issue,
                    })

    summary["average_score"] = round(total_score / len(health_records), 1)

    # Determine overall status
    if summary["critical"] > 0:
        summary["overall_status"] = "critical"
    elif summary["warning"] > 0:
        summary["overall_status"] = "warning"
    elif summary["healthy"] > 0:
        summary["overall_status"] = "healthy"
    else:
        summary["overall_status"] = "unknown"

    return summary
