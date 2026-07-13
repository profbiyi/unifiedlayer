"""
Seed Script: Three Fintech Demo Scenarios

Creates three demo organizations with realistic Nigerian fintech data setups,
used for prototype demonstrations and the guided-trial walkthrough video:

1. NairaLink Payments  — digital payment provider
   Paystack transactions + PostgreSQL settlement database -> unified warehouse
2. KoboVault Wallet    — mobile wallet platform
   MongoDB wallet activity + Google Sheets KYC register -> combined analytics
3. SwiftCredit MFB     — micro-lending startup
   PostgreSQL loan management system + MySQL repayments -> regulatory reporting

Each org gets an admin user, sources, a warehouse destination, scheduled
pipelines, and ~6 weeks of realistic run history (successes, a few failures,
believable row volumes) so every screen in the app looks alive.

Idempotent: organizations are matched by slug and skipped if they exist.
No real credentials are stored — all connector configs are placeholders.

Usage:
    python -m backend.scripts.seed_demo_scenarios

Environment Variables:
    DEMO_ADMIN_PASSWORD - password for the three demo admin users
                          (default: DemoTrial2026!)
"""
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from backend.database import get_db_session
from backend.models import (
    Organization,
    User,
    DataSource,
    Destination,
    Pipeline,
    PipelineRun,
    Role,
    UserRole,
)
from backend.models.pipeline import (
    PipelineStatus,
    SourceType,
    DestinationType,
    WriteModeEnum,
)
from backend.auth import get_password_hash

# Fixed seed so re-runs on a fresh DB produce the same believable history
rng = random.Random(20260713)

HISTORY_DAYS = 45

FAILURE_MESSAGES = [
    "Source API rate limit exceeded (HTTP 429). Run will be retried on the next schedule.",
    "Connection timeout after 30s while reaching the source database.",
    "Source returned malformed JSON for 3 records; run aborted (schema contract: freeze).",
    "Warehouse connection dropped mid-write; transaction rolled back.",
]

SCENARIOS = [
    {
        "org": {
            "name": "NairaLink Payments (Demo)",
            "slug": "demo-nairalink",
            "description": (
                "Demo scenario 1 — digital payment provider. Unifies Paystack "
                "transaction data with the internal settlement database for "
                "compliance reporting and performance tracking."
            ),
        },
        "admin": {
            "email": "demo.nairalink@unifiedlayer.io",
            "username": "demo_nairalink_admin",
            "full_name": "Adaeze Okafor",
        },
        "sources": [
            {
                "key": "paystack",
                "name": "Paystack — Live Transactions",
                "description": "Card, transfer, and USSD transactions with settlement and fee data.",
                "source_type": SourceType.PAYSTACK,
                "config": {"secret_key": "sk_demo_placeholder", "demo": True},
            },
            {
                "key": "settlements",
                "name": "Settlement Database",
                "description": "Internal PostgreSQL database holding daily settlement and payout records.",
                "source_type": SourceType.POSTGRES,
                "config": {
                    "host": "demo-settlements.internal",
                    "port": 5432,
                    "database": "settlements",
                    "username": "readonly_demo",
                    "password": "demo_placeholder",
                    "demo": True,
                },
            },
        ],
        "destination": {
            "name": "NairaLink Warehouse",
            "description": "Unified PostgreSQL warehouse for compliance reporting and analytics.",
        },
        "pipelines": [
            {
                "name": "Paystack Transactions → Warehouse",
                "description": "Syncs transactions, refunds, and disputes for a single unified payments view.",
                "source_key": "paystack",
                "schedule": "0 */6 * * *",
                "runs_per_day": 4,
                "rows_range": (800, 2600),
            },
            {
                "name": "Settlement Reconciliation Sync",
                "description": "Daily sync of settlement records used to reconcile payouts against transactions.",
                "source_key": "settlements",
                "schedule": "0 2 * * *",
                "runs_per_day": 1,
                "rows_range": (1200, 1900),
            },
        ],
    },
    {
        "org": {
            "name": "KoboVault Wallet (Demo)",
            "slug": "demo-kobovault",
            "description": (
                "Demo scenario 2 — mobile wallet platform. Combines wallet "
                "activity from MongoDB with the KYC compliance register so "
                "product and risk teams share one view."
            ),
        },
        "admin": {
            "email": "demo.kobovault@unifiedlayer.io",
            "username": "demo_kobovault_admin",
            "full_name": "Ibrahim Musa",
        },
        "sources": [
            {
                "key": "activity",
                "name": "Wallet Activity Store",
                "description": "MongoDB cluster with top-ups, peer transfers, and balance events.",
                "source_type": SourceType.MONGODB,
                "config": {
                    "connection_string": "mongodb://readonly_demo:demo_placeholder@demo-wallet.internal:27017",
                    "database": "wallet_events",
                    "demo": True,
                },
            },
            {
                "key": "kyc",
                "name": "KYC Compliance Register",
                "description": "Google Sheet maintained by the compliance team: verification tiers and BVN checks.",
                "source_type": SourceType.GOOGLE_SHEETS,
                "config": {"spreadsheet_id": "demo_placeholder", "demo": True},
            },
        ],
        "destination": {
            "name": "KoboVault Analytics Warehouse",
            "description": "PostgreSQL warehouse combining activity and compliance data.",
        },
        "pipelines": [
            {
                "name": "Wallet Activity Sync",
                "description": "Syncs user activity events — top-ups, transfers, balance changes.",
                "source_key": "activity",
                "schedule": "0 */4 * * *",
                "runs_per_day": 6,
                "rows_range": (2800, 9200),
            },
            {
                "name": "KYC Register Sync",
                "description": "Daily pull of the compliance register for regulator-ready user verification reporting.",
                "source_key": "kyc",
                "schedule": "0 5 * * *",
                "runs_per_day": 1,
                "rows_range": (40, 160),
            },
        ],
    },
    {
        "org": {
            "name": "SwiftCredit MFB (Demo)",
            "slug": "demo-swiftcredit",
            "description": (
                "Demo scenario 3 — micro-lending startup. Pulls loan "
                "disbursements and repayments into one data layer feeding "
                "credit scoring and CBN regulatory submissions."
            ),
        },
        "admin": {
            "email": "demo.swiftcredit@unifiedlayer.io",
            "username": "demo_swiftcredit_admin",
            "full_name": "Funmilayo Adeyemi",
        },
        "sources": [
            {
                "key": "loans",
                "name": "Loan Management System",
                "description": "PostgreSQL LMS with loan applications, approvals, and disbursements.",
                "source_type": SourceType.POSTGRES,
                "config": {
                    "host": "demo-lms.internal",
                    "port": 5432,
                    "database": "loans",
                    "username": "readonly_demo",
                    "password": "demo_placeholder",
                    "demo": True,
                },
            },
            {
                "key": "repayments",
                "name": "Repayments Database",
                "description": "MySQL database recording repayment schedules, collections, and defaults.",
                "source_type": SourceType.MYSQL,
                "config": {
                    "host": "demo-repayments.internal",
                    "port": 3306,
                    "database": "repayments",
                    "username": "readonly_demo",
                    "password": "demo_placeholder",
                    "demo": True,
                },
            },
        ],
        "destination": {
            "name": "SwiftCredit Reporting Warehouse",
            "description": "PostgreSQL warehouse feeding credit scoring and the CBN regulatory report template.",
        },
        "pipelines": [
            {
                "name": "Loan Disbursements Sync",
                "description": "Daily sync of disbursed loans with borrower, tenor, and rate fields for regulatory returns.",
                "source_key": "loans",
                "schedule": "0 1 * * *",
                "runs_per_day": 1,
                "rows_range": (110, 320),
            },
            {
                "name": "Repayments & Collections Sync",
                "description": "Twice-daily repayment collections feeding portfolio-at-risk and credit scoring models.",
                "source_key": "repayments",
                "schedule": "0 1,13 * * *",
                "runs_per_day": 2,
                "rows_range": (380, 950),
            },
        ],
    },
]


def build_run_history(pipeline: Pipeline, runs_per_day: int, rows_range: tuple) -> list:
    """Generate ~HISTORY_DAYS days of believable run history for a pipeline."""
    runs = []
    now = datetime.now(timezone.utc)
    interval_hours = 24 / runs_per_day

    for day in range(HISTORY_DAYS, 0, -1):
        for slot in range(runs_per_day):
            started = now - timedelta(days=day, hours=interval_hours * slot)
            # ~4% failure rate, everything else completes
            failed = rng.random() < 0.04
            rows = rng.randint(*rows_range)
            duration = round(rng.uniform(18, 240) * (rows / max(rows_range[1], 1)) + rng.uniform(5, 20), 1)

            run = PipelineRun(
                public_id=uuid.uuid4(),
                pipeline_id=pipeline.id,
                status=PipelineStatus.FAILED if failed else PipelineStatus.COMPLETED,
                started_at=started,
                completed_at=started + timedelta(seconds=duration),
                rows_read=rows if not failed else rng.randint(0, rows // 3),
                rows_written=rows if not failed else 0,
                bytes_read=rows * rng.randint(280, 520),
                bytes_written=0 if failed else rows * rng.randint(280, 520),
                duration_seconds=duration,
                error_message=rng.choice(FAILURE_MESSAGES) if failed else None,
                created_at=started,
            )
            runs.append(run)
    return runs


def seed_scenario(db: Session, scenario: dict, org_admin_role: Role, password_hash: str) -> None:
    org_cfg = scenario["org"]
    existing = db.query(Organization).filter(Organization.slug == org_cfg["slug"]).first()
    if existing:
        print(f"📋 {org_cfg['name']} already exists — skipping.")
        return

    print(f"📋 Creating {org_cfg['name']}...")
    now = datetime.now(timezone.utc)

    org = Organization(
        name=org_cfg["name"],
        slug=org_cfg["slug"],
        description=org_cfg["description"],
        subscription_plan="professional",
        subscription_status="trial",
        trial_ends_at=now + timedelta(days=15),
        max_users=3,
        is_active=True,
        can_sync_data=True,
        admin_onboarded=True,
    )
    db.add(org)
    db.flush()

    admin_cfg = scenario["admin"]
    admin = User(
        organization_id=org.id,
        email=admin_cfg["email"],
        username=admin_cfg["username"],
        full_name=admin_cfg["full_name"],
        hashed_password=password_hash,
        is_active=True,
        email_verified=True,
    )
    db.add(admin)
    db.flush()
    db.add(UserRole(user_id=admin.id, role_id=org_admin_role.id, organization_id=org.id))

    sources = {}
    for src_cfg in scenario["sources"]:
        source = DataSource(
            organization_id=org.id,
            name=src_cfg["name"],
            description=src_cfg["description"],
            source_type=src_cfg["source_type"],
            config=src_cfg["config"],
            is_active=True,
        )
        db.add(source)
        sources[src_cfg["key"]] = source
    db.flush()

    dest_cfg = scenario["destination"]
    destination = Destination(
        organization_id=org.id,
        name=dest_cfg["name"],
        description=dest_cfg["description"],
        destination_type=DestinationType.POSTGRES,
        config={
            "host": "demo-warehouse.internal",
            "port": 5432,
            "database": org_cfg["slug"].replace("-", "_"),
            "username": "warehouse_demo",
            "password": "demo_placeholder",
            "demo": True,
        },
        is_active=True,
    )
    db.add(destination)
    db.flush()

    total_runs = 0
    for pipe_cfg in scenario["pipelines"]:
        pipeline = Pipeline(
            organization_id=org.id,
            source_id=sources[pipe_cfg["source_key"]].id,
            destination_id=destination.id,
            name=pipe_cfg["name"],
            description=pipe_cfg["description"],
            schedule=pipe_cfg["schedule"],
            schedule_enabled=True,
            schedule_timezone="Africa/Lagos",
            write_mode=WriteModeEnum.MERGE,
            is_active=True,
            created_at=now - timedelta(days=HISTORY_DAYS + 3),
        )
        db.add(pipeline)
        db.flush()

        runs = build_run_history(pipeline, pipe_cfg["runs_per_day"], pipe_cfg["rows_range"])
        db.add_all(runs)
        total_runs += len(runs)

        last_run = max(runs, key=lambda r: r.started_at)
        pipeline.last_scheduled_run = last_run.started_at
        pipeline.next_scheduled_run = now + timedelta(hours=24 / pipe_cfg["runs_per_day"])

    db.commit()
    print(
        f"   ✅ {len(scenario['sources'])} sources, 1 destination, "
        f"{len(scenario['pipelines'])} pipelines, {total_runs} runs "
        f"(admin: {admin_cfg['email']})"
    )


def main():
    password = os.environ.get("DEMO_ADMIN_PASSWORD", "DemoTrial2026!")
    password_hash = get_password_hash(password)

    print("\n" + "=" * 60)
    print("Seeding fintech demo scenarios")
    print("=" * 60)

    db = get_db_session()
    try:
        org_admin_role = db.query(Role).filter(Role.slug == "org_admin").first()
        if not org_admin_role:
            print("❌ ORG_ADMIN role not found. Run: python -m backend.scripts.seed_rbac")
            sys.exit(1)

        for scenario in SCENARIOS:
            seed_scenario(db, scenario, org_admin_role, password_hash)
    finally:
        db.close()

    print("\nDone. Demo admin logins use DEMO_ADMIN_PASSWORD "
          "(default: DemoTrial2026!).\n")


if __name__ == "__main__":
    main()
