"""
Clear All Data Script.

WARNING: This will delete ALL data from the database (except roles and permissions).
Use this to reset the platform for fresh testing.
"""

import sys
from pathlib import Path

# Add parent directory to path
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
    UserRole,
    UserInvitation,
    AuditLog,
)
from backend.models.lineage import LineageNode, LineageEdge
from backend.models.quality import QualityCheck, PipelineQualityCheck, QualityCheckResult


def clear_all_data(db: Session, keep_roles: bool = True):
    """
    Clear all data from database.

    Args:
        db: Database session
        keep_roles: If True, keep roles and permissions intact
    """
    print("\n" + "="*60)
    print("⚠️  CLEARING ALL DATA FROM DATABASE")
    print("="*60 + "\n")

    # Order matters due to foreign key constraints
    tables_to_clear = [
        ("Quality Check Results", QualityCheckResult),
        ("Pipeline Quality Checks", PipelineQualityCheck),
        ("Quality Checks", QualityCheck),
        ("Lineage Edges", LineageEdge),
        ("Lineage Nodes", LineageNode),
        ("Pipeline Runs", PipelineRun),
        ("Pipelines", Pipeline),
        ("Destinations", Destination),
        ("Data Sources", DataSource),
        ("Audit Logs", AuditLog),
        ("User Invitations", UserInvitation),
        ("User Roles", UserRole),
        ("Users", User),
        ("Organizations", Organization),
    ]

    for table_name, model in tables_to_clear:
        try:
            count = db.query(model).count()
            if count > 0:
                db.query(model).delete()
                db.commit()
                print(f"✅ Deleted {count} records from {table_name}")
            else:
                print(f"ℹ️  {table_name}: No records to delete")
        except Exception as e:
            print(f"❌ Error deleting from {table_name}: {str(e)}")
            db.rollback()

    print("\n" + "="*60)
    print("✅ ALL DATA CLEARED SUCCESSFULLY!")
    print("="*60)
    print("\n📝 Note: Roles and permissions are preserved.")
    print("🔑 Create a super user with: python backend/scripts/create_superuser.py")
    print("\n" + "="*60 + "\n")


def main():
    """Main function."""
    # Confirmation prompt
    print("\n⚠️  WARNING: This will DELETE ALL DATA from the database!")
    print("This includes:")
    print("  - All organizations")
    print("  - All users")
    print("  - All pipelines and runs")
    print("  - All data sources and destinations")
    print("  - All lineage data")
    print("  - All quality checks")
    print("  - All audit logs")
    print("\nRoles and permissions will be preserved.\n")

    confirmation = input("Are you sure you want to continue? Type 'DELETE ALL' to confirm: ")

    if confirmation != "DELETE ALL":
        print("\n❌ Operation cancelled. No data was deleted.")
        return

    db = get_db_session()

    try:
        clear_all_data(db)
    except Exception as e:
        print(f"\n❌ Error clearing data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
