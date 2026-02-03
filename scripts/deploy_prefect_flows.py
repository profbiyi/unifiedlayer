#!/usr/bin/env python3
"""
Deploy Prefect flows to Prefect server.

This script registers the pipeline execution flow with Prefect server,
allowing it to be executed by Prefect workers.

Usage:
    python scripts/deploy_prefect_flows.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule
from datetime import timedelta

from backend.prefect_flows.pipeline_flow import execute_pipeline_flow


async def deploy_flows():
    """Deploy all Prefect flows to server."""

    print("🚀 Deploying Prefect flows...")

    # Deploy pipeline execution flow
    deployment = await Deployment.build_from_flow(
        flow=execute_pipeline_flow,
        name="production",
        version="1.0.0",
        work_pool_name="default-agent-pool",
        tags=["production", "pipeline", "etl"],
        description="Execute data pipeline from source to destination",
        parameters={},
    )

    deployment_id = await deployment.apply()

    print(f"✅ Deployed: execute-pipeline-flow/production")
    print(f"   Deployment ID: {deployment_id}")
    print(f"   Work Pool: default-agent-pool")

    print("\n📋 Next steps:")
    print("   1. Start Prefect server: docker-compose up -d prefect-server")
    print("   2. Start Prefect worker: docker-compose up -d prefect-worker")
    print("   3. View UI: http://localhost:4200")
    print("   4. Enable worker execution: Set USE_PREFECT_WORKER=true in .env")

    return deployment_id


if __name__ == "__main__":
    asyncio.run(deploy_flows())
