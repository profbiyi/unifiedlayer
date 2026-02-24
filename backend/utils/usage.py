"""
Usage metering utility.

Provides a convenience function for recording usage increments
and checking plan limits.
"""
from typing import Dict

from sqlalchemy.orm import Session

from backend.models.billing import (
    Subscription,
    SubscriptionPlan,
    PLAN_LIMITS,
)
from backend.services.billing_service import BillingService


def record_usage(
    db: Session,
    organization_id: int,
    rows: int = 0,
    api_calls: int = 0,
    pipeline_runs: int = 0,
) -> Dict:
    """
    Increment usage counters for the current month and check plan limits.

    Returns a dict with the updated record and an optional warnings list
    if the organization is near (>=80%) or over (>=100%) any limit.

    Example return:
        {
            "record": <UsageRecord>,
            "warnings": [
                {"metric": "rows_synced", "current": 9500, "limit": 10000, "percent": 95.0, "status": "near_limit"},
            ]
        }
    """
    record = BillingService.get_or_create_usage_record(db, organization_id)

    # Increment counters
    if rows:
        record.rows_synced += rows
    if api_calls:
        record.api_calls += api_calls
    if pipeline_runs:
        record.pipeline_runs += pipeline_runs

    # Track overage on rows
    if record.rows_limit > 0 and record.rows_synced > record.rows_limit:
        record.rows_overage = record.rows_synced - record.rows_limit

    db.commit()
    db.refresh(record)

    # Check limits and build warnings
    sub = db.query(Subscription).filter(
        Subscription.organization_id == organization_id
    ).first()
    plan = sub.plan if sub else SubscriptionPlan.STARTER
    limits = PLAN_LIMITS[plan]

    warnings = []
    checks = [
        ("rows_synced", record.rows_synced, limits["max_rows_per_month"]),
        ("api_calls", record.api_calls, record.api_calls_limit),
        ("pipeline_runs", record.pipeline_runs, limits["max_pipelines"]),
    ]

    for metric, current, limit in checks:
        if limit <= 0:  # Unlimited
            continue
        percent = round((current / limit) * 100, 1)
        if percent >= 100:
            warnings.append({
                "metric": metric,
                "current": current,
                "limit": limit,
                "percent": percent,
                "status": "over_limit",
            })
        elif percent >= 80:
            warnings.append({
                "metric": metric,
                "current": current,
                "limit": limit,
                "percent": percent,
                "status": "near_limit",
            })

    return {"record": record, "warnings": warnings}
