"""
Migration script to assign RBAC roles to existing users.

This script:
1. Assigns SUPER_ADMIN role to users with is_superuser=True
2. Assigns ORG_ADMIN role to the first user in each organization
3. Assigns ORG_USER role to all other users
4. Creates UserRole entries for all assignments
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import User, Role, UserRole


def migrate_users_to_rbac():
    """Migrate existing users to RBAC system."""
    db: Session = SessionLocal()

    try:
        print("Starting RBAC migration for existing users...")

        # Get all roles
        super_admin_role = db.query(Role).filter(Role.slug == 'super_admin').first()
        org_admin_role = db.query(Role).filter(Role.slug == 'org_admin').first()
        org_user_role = db.query(Role).filter(Role.slug == 'org_user').first()

        if not all([super_admin_role, org_admin_role, org_user_role]):
            print("ERROR: Roles not found! Please run seed_rbac.py first.")
            return

        # Get all users without roles
        # Use explicit join condition to avoid ambiguity (UserRole has 2 FKs to User)
        users_without_roles = db.query(User).outerjoin(
            UserRole, User.id == UserRole.user_id
        ).filter(
            UserRole.id is None
        ).all()

        if not users_without_roles:
            print("No users found without roles. Migration may have already been run.")
            return

        print(f"Found {len(users_without_roles)} users without RBAC roles")

        migrated_count = 0
        super_admins_count = 0
        org_admins_count = 0
        org_users_count = 0

        # Track which organizations have admin assigned
        orgs_with_admin = set()

        # Process users
        for user in users_without_roles:
            role_to_assign = None

            # Check if user is superuser (old system)
            if user.is_superuser:
                role_to_assign = super_admin_role
                super_admins_count += 1
                print(f"  - Assigning SUPER_ADMIN to {user.email} (is_superuser=True)")

            # Check if this is the first user in their organization
            elif user.organization_id and user.organization_id not in orgs_with_admin:
                role_to_assign = org_admin_role
                orgs_with_admin.add(user.organization_id)
                org_admins_count += 1
                org_name = user.organization.name if user.organization else "Unknown"
                print(f"  - Assigning ORG_ADMIN to {user.email} (first user in {org_name})")

            # All other users become org_user
            else:
                role_to_assign = org_user_role
                org_users_count += 1
                print(f"  - Assigning ORG_USER to {user.email}")

            # Create UserRole assignment
            if role_to_assign:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role_to_assign.id,
                    organization_id=user.organization_id,
                    assigned_by_id=None,  # System migration
                )
                db.add(user_role)
                migrated_count += 1

        # Commit all changes
        db.commit()

        print("\n✅ Migration completed successfully!")
        print(f"   Total users migrated: {migrated_count}")
        print(f"   - SUPER_ADMIN: {super_admins_count}")
        print(f"   - ORG_ADMIN: {org_admins_count}")
        print(f"   - ORG_USER: {org_users_count}")

        # Verify migration
        print("\nVerifying migration...")
        total_users = db.query(User).count()
        users_with_roles = db.query(User).join(
            UserRole, User.id == UserRole.user_id
        ).distinct().count()
        print(f"   Total users: {total_users}")
        print(f"   Users with roles: {users_with_roles}")

        if total_users == users_with_roles:
            print("   ✅ All users have roles assigned!")
        else:
            print(f"   ⚠️  Warning: {total_users - users_with_roles} users still without roles")

    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("RBAC User Migration Script")
    print("=" * 60)
    migrate_users_to_rbac()
    print("=" * 60)
