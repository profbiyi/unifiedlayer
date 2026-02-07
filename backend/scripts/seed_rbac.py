"""
Seed RBAC System with Initial Roles and Permissions

This script populates the database with:
1. Three roles: SUPER_ADMIN, ORG_ADMIN, ORG_USER
2. All necessary permissions
3. Role-permission mappings
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from backend.database import get_db_session
from backend.models.rbac import Role, Permission, RolePermission


def seed_roles(db: Session):
    """Create the three main roles"""
    roles_data = [
        {
            "name": "SUPER_ADMIN",
            "slug": "super_admin",
            "description": "Platform super admin with global access to all organizations",
            "scope": "global",
        },
        {
            "name": "ORG_ADMIN",
            "slug": "org_admin",
            "description": "Organization administrator who can manage their organization and invite users",
            "scope": "organization",
        },
        {
            "name": "ORG_USER",
            "slug": "org_user",
            "description": "Regular organization member with limited permissions",
            "scope": "organization",
        },
    ]

    roles = {}
    for role_data in roles_data:
        # Check if role already exists
        role = db.query(Role).filter(Role.slug == role_data["slug"]).first()
        if not role:
            role = Role(**role_data)
            db.add(role)
            print(f"✅ Created role: {role_data['name']}")
        else:
            print(f"ℹ️  Role already exists: {role_data['name']}")

        roles[role_data["slug"]] = role

    db.commit()
    return roles


def seed_permissions(db: Session):
    """Create all permissions"""
    permissions_data = [
        # Organization permissions
        {"resource": "organization", "action": "read", "description": "View organization details"},
        {"resource": "organization", "action": "update", "description": "Edit organization settings"},
        {"resource": "organization", "action": "delete", "description": "Delete organization"},
        {"resource": "organization", "action": "manage_users", "description": "Manage organization users and roles"},
        {"resource": "organization", "action": "create", "description": "Create new organizations (super admin only)"},

        # User permissions
        {"resource": "user", "action": "read", "description": "View users"},
        {"resource": "user", "action": "create", "description": "Invite/create users"},
        {"resource": "user", "action": "update", "description": "Update user details"},
        {"resource": "user", "action": "delete", "description": "Delete/remove users"},
        {"resource": "user", "action": "change_role", "description": "Change user roles"},

        # Pipeline permissions
        {"resource": "pipeline", "action": "create", "description": "Create new pipelines"},
        {"resource": "pipeline", "action": "read", "description": "View pipelines"},
        {"resource": "pipeline", "action": "update", "description": "Edit pipeline configuration"},
        {"resource": "pipeline", "action": "delete", "description": "Delete pipelines"},
        {"resource": "pipeline", "action": "execute", "description": "Trigger pipeline runs"},
        {"resource": "pipeline", "action": "monitor", "description": "View pipeline runs and logs"},

        # Source permissions
        {"resource": "source", "action": "create", "description": "Create data sources"},
        {"resource": "source", "action": "read", "description": "View data sources"},
        {"resource": "source", "action": "update", "description": "Edit data sources"},
        {"resource": "source", "action": "delete", "description": "Delete data sources"},

        # Destination permissions
        {"resource": "destination", "action": "create", "description": "Create destinations"},
        {"resource": "destination", "action": "read", "description": "View destinations"},
        {"resource": "destination", "action": "update", "description": "Edit destinations"},
        {"resource": "destination", "action": "delete", "description": "Delete destinations"},

        # Run permissions
        {"resource": "run", "action": "read", "description": "View pipeline runs"},
        {"resource": "run", "action": "cancel", "description": "Cancel running pipelines"},

        # Quality Check permissions
        {"resource": "quality_checks", "action": "create", "description": "Create quality checks"},
        {"resource": "quality_checks", "action": "read", "description": "View quality checks"},
        {"resource": "quality_checks", "action": "update", "description": "Edit quality checks"},
        {"resource": "quality_checks", "action": "delete", "description": "Delete quality checks"},

        # Metrics permissions
        {"resource": "metrics", "action": "read", "description": "View analytics and metrics"},

        # Settings permissions
        {"resource": "settings", "action": "read", "description": "View settings"},
        {"resource": "settings", "action": "update", "description": "Update settings"},

        # Audit permissions
        {"resource": "audit", "action": "read", "description": "View audit logs"},

        # dbt Project permissions
        {"resource": "dbt_project", "action": "create", "description": "Create dbt projects"},
        {"resource": "dbt_project", "action": "read", "description": "View dbt projects"},
        {"resource": "dbt_project", "action": "update", "description": "Edit dbt project configuration"},
        {"resource": "dbt_project", "action": "delete", "description": "Delete dbt projects"},
        {"resource": "dbt_project", "action": "execute", "description": "Trigger dbt runs"},
    ]

    permissions = {}
    for perm_data in permissions_data:
        key = f"{perm_data['resource']}:{perm_data['action']}"

        # Check if permission already exists
        perm = db.query(Permission).filter(
            Permission.resource == perm_data["resource"],
            Permission.action == perm_data["action"]
        ).first()

        if not perm:
            perm = Permission(**perm_data)
            db.add(perm)
            print(f"✅ Created permission: {key}")
        else:
            print(f"ℹ️  Permission already exists: {key}")

        permissions[key] = perm

    db.commit()
    return permissions


def assign_permissions_to_roles(db: Session, roles: dict, permissions: dict):
    """Assign permissions to each role"""

    # SUPER_ADMIN gets ALL permissions
    super_admin_perms = list(permissions.values())

    # ORG_ADMIN permissions (within their organization)
    org_admin_perms = [
        permissions["organization:read"],
        permissions["organization:update"],
        permissions["organization:manage_users"],
        permissions["user:read"],
        permissions["user:create"],
        permissions["user:update"],
        permissions["user:delete"],
        permissions["user:change_role"],
        permissions["pipeline:create"],
        permissions["pipeline:read"],
        permissions["pipeline:update"],
        permissions["pipeline:delete"],
        permissions["pipeline:execute"],
        permissions["pipeline:monitor"],
        permissions["source:create"],
        permissions["source:read"],
        permissions["source:update"],
        permissions["source:delete"],
        permissions["destination:create"],
        permissions["destination:read"],
        permissions["destination:update"],
        permissions["destination:delete"],
        permissions["run:read"],
        permissions["run:cancel"],
        permissions["quality_checks:create"],
        permissions["quality_checks:read"],
        permissions["quality_checks:update"],
        permissions["quality_checks:delete"],
        permissions["metrics:read"],
        permissions["settings:read"],
        permissions["settings:update"],
        permissions["audit:read"],
        permissions["dbt_project:create"],
        permissions["dbt_project:read"],
        permissions["dbt_project:update"],
        permissions["dbt_project:delete"],
        permissions["dbt_project:execute"],
    ]

    # ORG_USER permissions (limited)
    org_user_perms = [
        permissions["organization:read"],
        permissions["user:read"],
        permissions["pipeline:read"],
        permissions["pipeline:execute"],
        permissions["source:read"],
        permissions["destination:read"],
        permissions["run:read"],
        permissions["quality_checks:read"],
        permissions["metrics:read"],
        permissions["settings:read"],
        permissions["dbt_project:read"],
        permissions["dbt_project:execute"],
    ]

    role_permission_map = {
        "super_admin": super_admin_perms,
        "org_admin": org_admin_perms,
        "org_user": org_user_perms,
    }

    for role_slug, perms_list in role_permission_map.items():
        role = roles[role_slug]

        for perm in perms_list:
            # Check if assignment already exists
            role_perm = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id
            ).first()

            if not role_perm:
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.add(role_perm)

        print(f"✅ Assigned {len(perms_list)} permissions to {role.name}")

    db.commit()


def main():
    """Main seeding function"""
    print("\n" + "="*60)
    print("🌱 SEEDING RBAC SYSTEM")
    print("="*60 + "\n")

    db = get_db_session()

    try:
        print("📋 Step 1: Creating Roles...")
        roles = seed_roles(db)
        print()

        print("📋 Step 2: Creating Permissions...")
        permissions = seed_permissions(db)
        print()

        print("📋 Step 3: Assigning Permissions to Roles...")
        assign_permissions_to_roles(db, roles, permissions)
        print()

        print("="*60)
        print("✅ RBAC SYSTEM SEEDED SUCCESSFULLY!")
        print("="*60)
        print("\nRoles created:")
        print("  - SUPER_ADMIN (global scope)")
        print("  - ORG_ADMIN (organization scope)")
        print("  - ORG_USER (organization scope)")
        print(f"\nTotal permissions: {len(permissions)}")
        print("\n" + "="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Error seeding RBAC system: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
