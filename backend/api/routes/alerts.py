"""
Alert Settings API routes.

Manages notification channels, alert rules, and alert history for pipeline monitoring.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import uuid as uuid_mod

from backend.database import get_db
from backend.models.pipeline import User
from backend.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# --- Pydantic schemas ---

class SlackChannelConfig(BaseModel):
    enabled: bool = False
    webhook_url: Optional[str] = None


class EmailChannelConfig(BaseModel):
    enabled: bool = False
    recipients: List[str] = []


class NotificationChannelsConfig(BaseModel):
    slack: SlackChannelConfig = SlackChannelConfig()
    email: EmailChannelConfig = EmailChannelConfig()


class NotificationChannelsResponse(BaseModel):
    id: str
    organization_id: Optional[str] = None
    slack: SlackChannelConfig
    email: EmailChannelConfig
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertRuleConfig(BaseModel):
    id: str
    name: str
    description: str
    severity: str  # critical, warning, info
    enabled: bool = True
    threshold: Optional[float] = None
    threshold_unit: Optional[str] = None


class AlertRulesResponse(BaseModel):
    rules: List[AlertRuleConfig]
    updated_at: datetime


class UpdateAlertRuleRequest(BaseModel):
    enabled: Optional[bool] = None
    threshold: Optional[float] = None


class AlertHistoryItem(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str  # triggered, acknowledged, resolved
    message: str
    pipeline_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class PaginatedAlertHistory(BaseModel):
    items: List[AlertHistoryItem]
    total: int
    skip: int
    limit: int


class TestWebhookRequest(BaseModel):
    webhook_url: str


class TestWebhookResponse(BaseModel):
    success: bool
    message: str


# --- In-memory storage for demo (replace with DB in production) ---
# This would normally be stored in a database table

_notification_configs = {}
_alert_rules_configs = {}
_alert_history = {}

# Default alert rules
DEFAULT_ALERT_RULES = [
    AlertRuleConfig(
        id="pipeline_failure",
        name="Pipeline Failure",
        description="Alert when a pipeline run fails",
        severity="critical",
        enabled=True,
    ),
    AlertRuleConfig(
        id="slow_execution",
        name="Slow Execution",
        description="Alert when pipeline execution exceeds threshold",
        severity="warning",
        enabled=True,
        threshold=300,
        threshold_unit="seconds",
    ),
    AlertRuleConfig(
        id="data_quality_failure",
        name="Data Quality Check Failed",
        description="Alert when data quality checks fail",
        severity="critical",
        enabled=True,
    ),
    AlertRuleConfig(
        id="high_error_rate",
        name="High Error Rate",
        description="Alert when error rate exceeds threshold",
        severity="warning",
        enabled=True,
        threshold=5,
        threshold_unit="percent",
    ),
    AlertRuleConfig(
        id="source_connection_failed",
        name="Source Connection Failed",
        description="Alert when unable to connect to data source",
        severity="critical",
        enabled=True,
    ),
    AlertRuleConfig(
        id="destination_connection_failed",
        name="Destination Connection Failed",
        description="Alert when unable to connect to destination",
        severity="critical",
        enabled=True,
    ),
    AlertRuleConfig(
        id="schedule_missed",
        name="Scheduled Run Missed",
        description="Alert when a scheduled pipeline run is missed",
        severity="warning",
        enabled=False,
    ),
    AlertRuleConfig(
        id="low_row_count",
        name="Low Row Count",
        description="Alert when extracted rows fall below threshold",
        severity="info",
        enabled=False,
        threshold=100,
        threshold_unit="rows",
    ),
]


def _get_org_key(user: User) -> str:
    """Get organization key for storing configs."""
    return str(user.organization_id) if user.organization_id else f"user_{user.id}"


# --- Endpoints ---

@router.get("/settings/notifications", response_model=NotificationChannelsResponse)
async def get_notification_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get notification channel configuration for the organization."""
    org_key = _get_org_key(current_user)

    if org_key not in _notification_configs:
        # Return default config
        _notification_configs[org_key] = {
            "id": str(uuid_mod.uuid4()),
            "organization_id": org_key,
            "slack": SlackChannelConfig(),
            "email": EmailChannelConfig(),
            "updated_at": datetime.utcnow(),
        }

    config = _notification_configs[org_key]
    return NotificationChannelsResponse(
        id=config["id"],
        organization_id=config["organization_id"],
        slack=config["slack"],
        email=config["email"],
        updated_at=config["updated_at"],
    )


@router.put("/settings/notifications", response_model=NotificationChannelsResponse)
async def update_notification_channels(
    config: NotificationChannelsConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update notification channel configuration."""
    org_key = _get_org_key(current_user)

    existing = _notification_configs.get(org_key, {})

    _notification_configs[org_key] = {
        "id": existing.get("id", str(uuid_mod.uuid4())),
        "organization_id": org_key,
        "slack": config.slack,
        "email": config.email,
        "updated_at": datetime.utcnow(),
    }

    updated = _notification_configs[org_key]
    return NotificationChannelsResponse(
        id=updated["id"],
        organization_id=updated["organization_id"],
        slack=updated["slack"],
        email=updated["email"],
        updated_at=updated["updated_at"],
    )


@router.post("/settings/notifications/test-slack", response_model=TestWebhookResponse)
async def test_slack_webhook(
    request: TestWebhookRequest,
    current_user: User = Depends(get_current_user),
):
    """Test a Slack webhook URL by sending a test message."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                request.webhook_url,
                json={
                    "text": "Test message from UnifiedLayer Alerts",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*UnifiedLayer Alert Test*\nThis is a test message to verify your Slack webhook is configured correctly."
                            }
                        }
                    ]
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                return TestWebhookResponse(
                    success=True,
                    message="Test message sent successfully! Check your Slack channel."
                )
            else:
                return TestWebhookResponse(
                    success=False,
                    message=f"Slack returned status {response.status_code}: {response.text}"
                )
    except httpx.TimeoutException:
        return TestWebhookResponse(
            success=False,
            message="Request timed out. Please check the webhook URL."
        )
    except Exception as e:
        return TestWebhookResponse(
            success=False,
            message=f"Failed to send test message: {str(e)}"
        )


@router.get("/rules", response_model=AlertRulesResponse)
async def get_alert_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all alert rules for the organization."""
    org_key = _get_org_key(current_user)

    if org_key not in _alert_rules_configs:
        # Initialize with default rules
        _alert_rules_configs[org_key] = {
            "rules": [rule.model_copy() for rule in DEFAULT_ALERT_RULES],
            "updated_at": datetime.utcnow(),
        }

    config = _alert_rules_configs[org_key]
    return AlertRulesResponse(
        rules=config["rules"],
        updated_at=config["updated_at"],
    )


@router.patch("/rules/{rule_id}", response_model=AlertRuleConfig)
async def update_alert_rule(
    rule_id: str,
    update: UpdateAlertRuleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a specific alert rule."""
    org_key = _get_org_key(current_user)

    if org_key not in _alert_rules_configs:
        _alert_rules_configs[org_key] = {
            "rules": [rule.model_copy() for rule in DEFAULT_ALERT_RULES],
            "updated_at": datetime.utcnow(),
        }

    rules = _alert_rules_configs[org_key]["rules"]

    for i, rule in enumerate(rules):
        if rule.id == rule_id:
            if update.enabled is not None:
                rule.enabled = update.enabled
            if update.threshold is not None:
                rule.threshold = update.threshold

            _alert_rules_configs[org_key]["rules"][i] = rule
            _alert_rules_configs[org_key]["updated_at"] = datetime.utcnow()

            return rule

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert rule '{rule_id}' not found"
    )


@router.get("/history", response_model=PaginatedAlertHistory)
async def get_alert_history(
    severity: Optional[str] = Query(None, description="Filter by severity (critical, warning, info)"),
    alert_status: Optional[str] = Query(None, description="Filter by status (triggered, acknowledged, resolved)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get alert history for the organization."""
    org_key = _get_org_key(current_user)

    if org_key not in _alert_history:
        # Return sample data for demo
        _alert_history[org_key] = _generate_sample_alerts()

    alerts = _alert_history[org_key]

    # Apply filters
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    if alert_status:
        alerts = [a for a in alerts if a["status"] == alert_status]

    # Sort by triggered_at descending
    alerts = sorted(alerts, key=lambda x: x["triggered_at"], reverse=True)

    total = len(alerts)
    items = alerts[skip:skip + limit]

    return PaginatedAlertHistory(
        items=[AlertHistoryItem(**a) for a in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/history/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Acknowledge an alert."""
    org_key = _get_org_key(current_user)

    if org_key not in _alert_history:
        raise HTTPException(status_code=404, detail="Alert not found")

    for alert in _alert_history[org_key]:
        if alert["id"] == alert_id:
            alert["status"] = "acknowledged"
            alert["acknowledged_at"] = datetime.utcnow()
            return {"success": True, "message": "Alert acknowledged"}

    raise HTTPException(status_code=404, detail="Alert not found")


@router.patch("/history/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve an alert."""
    org_key = _get_org_key(current_user)

    if org_key not in _alert_history:
        raise HTTPException(status_code=404, detail="Alert not found")

    for alert in _alert_history[org_key]:
        if alert["id"] == alert_id:
            alert["status"] = "resolved"
            alert["resolved_at"] = datetime.utcnow()
            return {"success": True, "message": "Alert resolved"}

    raise HTTPException(status_code=404, detail="Alert not found")


def _generate_sample_alerts() -> List[dict]:
    """Generate sample alert history for demo purposes."""
    from datetime import timedelta

    now = datetime.utcnow()

    return [
        {
            "id": str(uuid_mod.uuid4()),
            "rule_id": "pipeline_failure",
            "rule_name": "Pipeline Failure",
            "severity": "critical",
            "status": "triggered",
            "message": "Pipeline 'Sales Data Sync' failed with error: Connection timeout",
            "pipeline_id": "pipe_001",
            "pipeline_name": "Sales Data Sync",
            "triggered_at": now - timedelta(hours=1),
            "acknowledged_at": None,
            "resolved_at": None,
        },
        {
            "id": str(uuid_mod.uuid4()),
            "rule_id": "slow_execution",
            "rule_name": "Slow Execution",
            "severity": "warning",
            "status": "acknowledged",
            "message": "Pipeline 'Customer Analytics' took 450 seconds (threshold: 300s)",
            "pipeline_id": "pipe_002",
            "pipeline_name": "Customer Analytics",
            "triggered_at": now - timedelta(hours=3),
            "acknowledged_at": now - timedelta(hours=2),
            "resolved_at": None,
        },
        {
            "id": str(uuid_mod.uuid4()),
            "rule_id": "data_quality_failure",
            "rule_name": "Data Quality Check Failed",
            "severity": "critical",
            "status": "resolved",
            "message": "Null check failed: 15% null values in 'email' column (threshold: 5%)",
            "pipeline_id": "pipe_003",
            "pipeline_name": "User Data Import",
            "triggered_at": now - timedelta(days=1),
            "acknowledged_at": now - timedelta(days=1) + timedelta(hours=1),
            "resolved_at": now - timedelta(hours=12),
        },
        {
            "id": str(uuid_mod.uuid4()),
            "rule_id": "source_connection_failed",
            "rule_name": "Source Connection Failed",
            "severity": "critical",
            "status": "resolved",
            "message": "Failed to connect to PostgreSQL source 'Production DB'",
            "pipeline_id": "pipe_004",
            "pipeline_name": "Product Inventory",
            "triggered_at": now - timedelta(days=2),
            "acknowledged_at": now - timedelta(days=2) + timedelta(minutes=30),
            "resolved_at": now - timedelta(days=2) + timedelta(hours=2),
        },
        {
            "id": str(uuid_mod.uuid4()),
            "rule_id": "low_row_count",
            "rule_name": "Low Row Count",
            "severity": "info",
            "status": "resolved",
            "message": "Pipeline extracted only 45 rows (threshold: 100 rows)",
            "pipeline_id": "pipe_005",
            "pipeline_name": "Daily Reports",
            "triggered_at": now - timedelta(days=3),
            "acknowledged_at": None,
            "resolved_at": now - timedelta(days=3) + timedelta(hours=6),
        },
    ]
