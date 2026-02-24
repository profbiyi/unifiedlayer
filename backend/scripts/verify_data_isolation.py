"""
Verify multi-tenant data isolation.

This script checks that pipeline runs are properly associated with
the correct pipelines and organizations.
"""
from backend.database import get_db_session
from backend.models.pipeline import Pipeline, PipelineRun, Organization


def verify_isolation():
    """Check data isolation integrity."""
    db = get_db_session()

    print("=" * 60)
    print("MULTI-TENANT DATA ISOLATION CHECK")
    print("=" * 60)

    try:
        # Check 1: All pipeline runs have valid pipeline_id
        print("\n1. Checking pipeline_id integrity...")
        invalid_runs = db.query(PipelineRun).outerjoin(Pipeline).filter(
            Pipeline.id is None
        ).count()

        if invalid_runs > 0:
            print(f"   ❌ ISSUE: {invalid_runs} runs have invalid pipeline_id")

            # Show details
            bad_runs = db.query(PipelineRun).outerjoin(Pipeline).filter(
                Pipeline.id is None
            ).limit(10).all()

            for run in bad_runs:
                print(f"      Run ID: {run.id}, Invalid pipeline_id: {run.pipeline_id}")
        else:
            print("   ✅ All runs have valid pipeline_id")

        # Check 2: Verify organization isolation
        print("\n2. Checking organization isolation...")
        orgs = db.query(Organization).all()

        isolation_issues = []
        for org in orgs:
            # Get pipelines for this org
            org_pipelines = db.query(Pipeline).filter(
                Pipeline.organization_id == org.id
            ).all()

            org_pipeline_ids = [p.id for p in org_pipelines]

            # Get runs for this org's pipelines
            org_runs = db.query(PipelineRun).filter(
                PipelineRun.pipeline_id.in_(org_pipeline_ids)
            ).all()

            # Check if any runs belong to pipelines from other orgs
            for run in org_runs:
                run_pipeline = db.query(Pipeline).filter(
                    Pipeline.id == run.pipeline_id
                ).first()

                if run_pipeline and run_pipeline.organization_id != org.id:
                    isolation_issues.append({
                        'run_id': run.id,
                        'run_org': org.name,
                        'pipeline_org': run_pipeline.organization.name,
                    })

        if isolation_issues:
            print(f"   ❌ ISSUE: {len(isolation_issues)} isolation violations found")
            for issue in isolation_issues[:10]:
                print(f"      Run {issue['run_id']}: belongs to '{issue['run_org']}' but shows in '{issue['pipeline_org']}'")
        else:
            print("   ✅ No organization isolation issues")

        # Check 3: Statistics per organization
        print("\n3. Organization statistics...")
        for org in orgs:
            pipeline_count = db.query(Pipeline).filter(
                Pipeline.organization_id == org.id
            ).count()

            run_count = db.query(PipelineRun).join(Pipeline).filter(
                Pipeline.organization_id == org.id
            ).count()

            print(f"   {org.name}:")
            print(f"      Pipelines: {pipeline_count}")
            print(f"      Runs: {run_count}")

        # Check 4: Find any orphaned runs
        print("\n4. Checking for orphaned runs...")
        total_runs = db.query(PipelineRun).count()
        runs_with_pipelines = db.query(PipelineRun).join(Pipeline).count()
        orphaned = total_runs - runs_with_pipelines

        if orphaned > 0:
            print(f"   ❌ ISSUE: {orphaned} orphaned runs (no valid pipeline)")

            # Clean them up?
            print("\n   Do you want to delete orphaned runs? (This script won't do it automatically)")
        else:
            print("   ✅ No orphaned runs")

        # Summary
        print("\n" + "=" * 60)
        if invalid_runs == 0 and len(isolation_issues) == 0 and orphaned == 0:
            print("✅ DATA ISOLATION VERIFIED - All checks passed!")
        else:
            print("❌ DATA ISOLATION ISSUES FOUND - Review above")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    verify_isolation()
