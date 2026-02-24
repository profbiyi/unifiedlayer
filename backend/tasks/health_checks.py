"""
Health Check Celery Tasks.

Periodic tasks for checking health of sources, pipelines, and destinations.
Runs every 15 minutes and triggers alerts for unhealthy resources.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from celery import Task
from celery.schedules import crontab

from backend.celery_app import celery_app, BaseTask
from backend.database import SessionLocal
from backend.models.pipeline import DataSource, Pipeline, Destination, Organization
from backend.models.health import ResourceHealth, HealthStatus, ResourceType
from backend.services.health_monitor import (
    get_source_health,
    get_pipeline_health,
    get_destination_health,
    save_health_status,
)

logger = logging.getLogger(__name__)


class HealthCheckTask(BaseTask):
    """Base class for health check tasks."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300  # Max 5 minutes between retries
    max_retries = 2
    soft_time_limit = 600  # 10 minute soft limit
    time_limit = 660  # 11 minute hard limit


@celery_app.task(
    bind=True,
    base=HealthCheckTask,
    name="backend.tasks.health_checks.run_all_health_checks",
)
def run_all_health_checks(self: Task) -> Dict[str, Any]:
    """
    Run health checks for all resources across all organizations.

    This task is scheduled to run every 15 minutes.

    Returns:
        Dictionary with check results summary
    """
    db = SessionLocal()
    try:
        start_time = datetime.now(timezone.utc)
        logger.info("Starting scheduled health checks for all organizations")

        results = {
            "started_at": start_time.isoformat(),
            "organizations_checked": 0,
            "sources_checked": 0,
            "pipelines_checked": 0,
            "destinations_checked": 0,
            "critical_issues_found": 0,
            "alerts_triggered": 0,
        }

        # Get all active organizations
        organizations = db.query(Organization).filter(
            Organization.is_active
        ).all()

        for org in organizations:
            try:
                org_results = _check_organization_health(db, org.id)
                results["organizations_checked"] += 1
                results["sources_checked"] += org_results.get("sources_checked", 0)
                results["pipelines_checked"] += org_results.get("pipelines_checked", 0)
                results["destinations_checked"] += org_results.get("destinations_checked", 0)
                results["critical_issues_found"] += org_results.get("critical_issues", 0)
                results["alerts_triggered"] += org_results.get("alerts_triggered", 0)
            except Exception as e:
                logger.error(f"Health check failed for organization {org.id}: {str(e)}")

        end_time = datetime.now(timezone.utc)
        results["completed_at"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Health checks completed: {results['sources_checked']} sources, "
            f"{results['pipelines_checked']} pipelines, "
            f"{results['destinations_checked']} destinations checked. "
            f"Critical issues: {results['critical_issues_found']}"
        )

        return results

    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=HealthCheckTask,
    name="backend.tasks.health_checks.check_organization_health",
)
def check_organization_health(self: Task, organization_id: int) -> Dict[str, Any]:
    """
    Run health checks for a specific organization.

    Args:
        organization_id: The organization ID to check

    Returns:
        Dictionary with check results for the organization
    """
    db = SessionLocal()
    try:
        logger.info(f"Running health checks for organization {organization_id}")
        results = _check_organization_health(db, organization_id)
        logger.info(f"Health checks completed for organization {organization_id}: {results}")
        return results
    finally:
        db.close()


def _check_organization_health(db, organization_id: int) -> Dict[str, Any]:
    """
    Internal function to check health for an organization.

    Args:
        db: Database session
        organization_id: Organization ID

    Returns:
        Dictionary with check results
    """
    results = {
        "organization_id": organization_id,
        "sources_checked": 0,
        "pipelines_checked": 0,
        "destinations_checked": 0,
        "critical_issues": 0,
        "alerts_triggered": 0,
        "status_changes": [],
    }

    # Check all sources
    sources = db.query(DataSource).filter(
        DataSource.organization_id == organization_id,
        DataSource.is_active,
    ).all()

    for source in sources:
        try:
            # Get previous health status
            prev_health = db.query(ResourceHealth).filter(
                ResourceHealth.organization_id == organization_id,
                ResourceHealth.resource_type == ResourceType.SOURCE,
                ResourceHealth.resource_id == source.id,
            ).first()
            prev_status = prev_health.status if prev_health else None

            # Run health check (skip connection test for scheduled checks to reduce load)
            health_data = get_source_health(source, db, run_connection_test=False)
            health = save_health_status(db, organization_id, health_data, "scheduled")
            results["sources_checked"] += 1

            # Check for status change
            if prev_status and health.status != prev_status:
                results["status_changes"].append({
                    "type": "source",
                    "id": source.id,
                    "name": source.name,
                    "from": prev_status.value if prev_status else None,
                    "to": health.status.value,
                })

            # Count critical issues
            if health.status == HealthStatus.CRITICAL:
                results["critical_issues"] += 1
                # Trigger alert for critical source issues
                alert_result = _trigger_health_alert(
                    db=db,
                    organization_id=organization_id,
                    resource_type="source",
                    resource_id=source.id,
                    resource_name=source.name,
                    health=health,
                )
                if alert_result:
                    results["alerts_triggered"] += 1

        except Exception as e:
            logger.error(f"Failed to check health for source {source.id}: {str(e)}")

    # Check all pipelines
    pipelines = db.query(Pipeline).filter(
        Pipeline.organization_id == organization_id,
        Pipeline.is_active,
    ).all()

    for pipeline in pipelines:
        try:
            # Get previous health status
            prev_health = db.query(ResourceHealth).filter(
                ResourceHealth.organization_id == organization_id,
                ResourceHealth.resource_type == ResourceType.PIPELINE,
                ResourceHealth.resource_id == pipeline.id,
            ).first()
            prev_status = prev_health.status if prev_health else None

            # Run health check
            health_data = get_pipeline_health(pipeline, db)
            health = save_health_status(db, organization_id, health_data, "scheduled")
            results["pipelines_checked"] += 1

            # Check for status change
            if prev_status and health.status != prev_status:
                results["status_changes"].append({
                    "type": "pipeline",
                    "id": pipeline.id,
                    "name": pipeline.name,
                    "from": prev_status.value if prev_status else None,
                    "to": health.status.value,
                })

            # Count critical issues
            if health.status == HealthStatus.CRITICAL:
                results["critical_issues"] += 1
                # Trigger alert for critical pipeline issues
                alert_result = _trigger_health_alert(
                    db=db,
                    organization_id=organization_id,
                    resource_type="pipeline",
                    resource_id=pipeline.id,
                    resource_name=pipeline.name,
                    health=health,
                )
                if alert_result:
                    results["alerts_triggered"] += 1

        except Exception as e:
            logger.error(f"Failed to check health for pipeline {pipeline.id}: {str(e)}")

    # Check all destinations
    destinations = db.query(Destination).filter(
        Destination.organization_id == organization_id,
        Destination.is_active,
    ).all()

    for destination in destinations:
        try:
            # Get previous health status
            prev_health = db.query(ResourceHealth).filter(
                ResourceHealth.organization_id == organization_id,
                ResourceHealth.resource_type == ResourceType.DESTINATION,
                ResourceHealth.resource_id == destination.id,
            ).first()
            prev_status = prev_health.status if prev_health else None

            # Run health check (skip connection test for scheduled checks)
            health_data = get_destination_health(destination, db, run_connection_test=False)
            health = save_health_status(db, organization_id, health_data, "scheduled")
            results["destinations_checked"] += 1

            # Check for status change
            if prev_status and health.status != prev_status:
                results["status_changes"].append({
                    "type": "destination",
                    "id": destination.id,
                    "name": destination.name,
                    "from": prev_status.value if prev_status else None,
                    "to": health.status.value,
                })

            # Count critical issues
            if health.status == HealthStatus.CRITICAL:
                results["critical_issues"] += 1
                # Trigger alert for critical destination issues
                alert_result = _trigger_health_alert(
                    db=db,
                    organization_id=organization_id,
                    resource_type="destination",
                    resource_id=destination.id,
                    resource_name=destination.name,
                    health=health,
                )
                if alert_result:
                    results["alerts_triggered"] += 1

        except Exception as e:
            logger.error(f"Failed to check health for destination {destination.id}: {str(e)}")

    return results


def _trigger_health_alert(
    db,
    organization_id: int,
    resource_type: str,
    resource_id: int,
    resource_name: str,
    health: ResourceHealth,
) -> bool:
    """
    Trigger an alert for a critical health issue.

    Args:
        db: Database session
        organization_id: Organization ID
        resource_type: Type of resource (source, pipeline, destination)
        resource_id: Resource ID
        resource_name: Resource name for display
        health: ResourceHealth model with issues

    Returns:
        True if alert was triggered successfully
    """
    try:
        # Get the most critical issue
        critical_issues = [i for i in (health.issues or []) if i.get("severity") == "critical"]
        if not critical_issues:
            return False

        issue = critical_issues[0]

        # Create notification
        from backend.models.notification import Notification

        # Get all users in the organization to notify
        from backend.models.pipeline import User

        users = db.query(User).filter(
            User.organization_id == organization_id,
            User.is_active,
        ).all()

        for user in users:
            notification = Notification(
                user_id=user.id,
                organization_id=organization_id,
                title=f"Health Alert: {resource_type.title()} '{resource_name}'",
                message=issue.get("message", "Critical health issue detected"),
                notification_type="health_alert",
                severity="critical",
                metadata={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "issue_code": issue.get("code"),
                    "health_score": health.score,
                },
            )
            db.add(notification)

        db.commit()

        logger.info(
            f"Health alert triggered for {resource_type} '{resource_name}' "
            f"(org: {organization_id}): {issue.get('message')}"
        )

        # Also try to send Slack/email alerts if configured
        _send_external_health_alert(
            db=db,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_name=resource_name,
            issue=issue,
            health_score=health.score,
        )

        return True

    except Exception as e:
        logger.error(f"Failed to trigger health alert: {str(e)}")
        return False


def _send_external_health_alert(
    db,
    organization_id: int,
    resource_type: str,
    resource_name: str,
    issue: Dict[str, Any],
    health_score: float,
):
    """
    Send health alert to external channels (Slack, email).

    This is a best-effort operation - failures are logged but don't affect the main flow.
    """
    try:
        import httpx

        # Try to get Slack webhook from organization settings
        # Note: This uses the in-memory alert configs from alerts.py
        # In production, this would be stored in the database
        from backend.api.routes.alerts import _notification_configs

        org_key = str(organization_id)
        config = _notification_configs.get(org_key, {})

        slack_config = config.get("slack", {})
        if isinstance(slack_config, dict):
            slack_enabled = slack_config.get("enabled", False)
            webhook_url = slack_config.get("webhook_url")
        else:
            slack_enabled = getattr(slack_config, 'enabled', False)
            webhook_url = getattr(slack_config, 'webhook_url', None)

        if slack_enabled and webhook_url:
            # Send Slack message
            severity_emoji = {
                "critical": ":red_circle:",
                "warning": ":large_orange_circle:",
                "info": ":large_blue_circle:",
            }.get(issue.get("severity", "info"), ":white_circle:")

            message = {
                "text": f"{severity_emoji} Health Alert: {resource_type.title()} '{resource_name}'",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{severity_emoji} Health Alert",
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Resource:*\n{resource_type.title()}: {resource_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Health Score:*\n{health_score:.0f}/100"
                            },
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Issue:* {issue.get('message', 'Unknown issue')}"
                        }
                    },
                ]
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook_url, json=message)
                if response.status_code != 200:
                    logger.warning(f"Slack alert failed with status {response.status_code}")

    except Exception as e:
        logger.warning(f"Failed to send external health alert: {str(e)}")


@celery_app.task(
    bind=True,
    base=HealthCheckTask,
    name="backend.tasks.health_checks.check_source_connectivity",
)
def check_source_connectivity(self: Task, source_id: int, organization_id: int) -> Dict[str, Any]:
    """
    Run a connection test for a specific source.

    This task can be triggered manually to test source connectivity.

    Args:
        source_id: The source internal ID
        organization_id: The organization ID

    Returns:
        Dictionary with connection test results
    """
    db = SessionLocal()
    try:
        source = db.query(DataSource).filter(
            DataSource.id == source_id,
            DataSource.organization_id == organization_id,
        ).first()

        if not source:
            return {"error": "Source not found", "success": False}

        # Run health check with connection test
        health_data = get_source_health(source, db, run_connection_test=True)
        health = save_health_status(db, organization_id, health_data, "manual")

        logger.info(f"Connection test completed for source {source_id}: status={health.status.value}")

        return {
            "success": health.status != HealthStatus.CRITICAL,
            "status": health.status.value,
            "score": health.score,
            "issues": health.issues,
            "metrics": health.metrics,
        }

    finally:
        db.close()


# Register periodic task with Celery Beat
celery_app.conf.beat_schedule["health-checks-every-15-minutes"] = {
    "task": "backend.tasks.health_checks.run_all_health_checks",
    "schedule": crontab(minute="*/15"),  # Every 15 minutes
    "options": {"queue": "health"},
}

# Add health queue to task routes
celery_app.conf.task_routes.update({
    "backend.tasks.health_checks.*": {"queue": "health"},
})
