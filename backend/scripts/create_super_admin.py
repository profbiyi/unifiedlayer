"""
Bootstrap Script: Create First Super Admin User

This script creates the initial super admin user for the platform.
The super admin can then create organizations and manage the entire platform.

Usage:
    python -m backend.scripts.create_super_admin

Environment Variables (optional):
    SUPER_ADMIN_EMAIL - Default: admin@unifiedlayer.io
    SUPER_ADMIN_USERNAME - Default: superadmin
    SUPER_ADMIN_PASSWORD - Default: changeme123 (CHANGE THIS!)
    SUPER_ADMIN_FULLNAME - Default: Super Administrator
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from backend.database import get_db_session
from backend.models import User, Organization, Role, UserRole
from backend.auth import get_password_hash
import getpass


def create_super_admin(
    email: str,
    username: str,
    password: str,
    full_name: str,
    db: Session
):
    """
    Create a super admin user.

    Args:
        email: Super admin email
        username: Super admin username
        password: Super admin password
        full_name: Super admin full name
        db: Database session

    Returns:
        Created user object
    """
    # Check if super admin already exists
    existing_user = db.query(User).filter(
        (User.email == email) | (User.username == username)
    ).first()

    if existing_user:
        print(f"\n📋 User '{email}' already exists. Updating password...")
        existing_user.hashed_password = get_password_hash(password)
        existing_user.is_active = True
        existing_user.is_superuser = True
        existing_user.email_verified = True
        db.commit()
        print(f"   ✅ Password updated for: {existing_user.email}")
        return existing_user

    # Check if super admin organization exists
    super_admin_org = db.query(Organization).filter(
        Organization.slug == "platform-admin"
    ).first()

    if not super_admin_org:
        print("\n📋 Creating Super Admin organization...")
        super_admin_org = Organization(
            name="Platform Administration",
            slug="platform-admin",
            description="Internal organization for platform super administrators",
            subscription_plan="enterprise",
            max_users=100,
            is_active=True,
            can_sync_data=True,
            subscription_status="active",
            admin_onboarded=True,  # Platform admin is always onboarded
        )
        db.add(super_admin_org)
        db.flush()
        print(f"   ✅ Created organization: {super_admin_org.name}")
    else:
        # Ensure platform-admin org is marked as onboarded
        if not super_admin_org.admin_onboarded:
            super_admin_org.admin_onboarded = True
            db.flush()
        print(f"\n📋 Using existing Super Admin organization: {super_admin_org.name}")

    # Create super admin user
    print(f"\n📋 Creating Super Admin user...")
    super_admin_user = User(
        organization_id=super_admin_org.id,
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=True,  # Legacy field for compatibility
        email_verified=True,
    )

    db.add(super_admin_user)
    db.flush()
    print(f"   ✅ Created user: {email}")

    # Assign SUPER_ADMIN role
    super_admin_role = db.query(Role).filter(Role.slug == "super_admin").first()

    if not super_admin_role:
        print("\n❌ SUPER_ADMIN role not found in database!")
        print("   Please run: python -m backend.scripts.seed_rbac")
        db.rollback()
        return None

    print(f"\n📋 Assigning SUPER_ADMIN role...")
    user_role = UserRole(
        user_id=super_admin_user.id,
        role_id=super_admin_role.id,
        organization_id=super_admin_org.id,
        assigned_by_id=None,  # Bootstrap, no assigner
    )
    db.add(user_role)

    # Commit all changes
    db.commit()
    db.refresh(super_admin_user)

    print(f"   ✅ Assigned SUPER_ADMIN role")

    return super_admin_user


def interactive_mode(db: Session):
    """Run in interactive mode, prompting for credentials."""
    print("\n" + "="*60)
    print("🚀 SUPER ADMIN CREATION - INTERACTIVE MODE")
    print("="*60 + "\n")

    print("Please provide the following information:")
    print("(Press Enter to use default values)\n")

    # Get email
    default_email = "admin@unifiedlayer.io"
    email = input(f"Email [{default_email}]: ").strip() or default_email

    # Get username
    default_username = "superadmin"
    username = input(f"Username [{default_username}]: ").strip() or default_username

    # Get full name
    default_fullname = "Super Administrator"
    full_name = input(f"Full Name [{default_fullname}]: ").strip() or default_fullname

    # Get password (secure input)
    while True:
        password = getpass.getpass("Password (min 8 chars): ").strip()
        if len(password) < 8:
            print("❌ Password must be at least 8 characters!")
            continue

        password_confirm = getpass.getpass("Confirm Password: ").strip()
        if password != password_confirm:
            print("❌ Passwords do not match!")
            continue

        break

    # Confirm
    print(f"\n📋 Creating Super Admin with:")
    print(f"   Email: {email}")
    print(f"   Username: {username}")
    print(f"   Full Name: {full_name}")

    confirm = input("\nProceed? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled by user")
        return

    # Create user
    user = create_super_admin(email, username, password, full_name, db)

    if user:
        print("\n" + "="*60)
        print("✅ SUPER ADMIN CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"\nCredentials:")
        print(f"  Email/Username: {email} or {username}")
        print(f"  Password: (as entered)")
        print(f"\nYou can now:")
        print(f"  1. Login at: http://localhost:3000/login")
        print(f"  2. Access Admin Dashboard: http://localhost:3000/admin")
        print(f"  3. Create organizations and invite users")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
        print("="*60 + "\n")


def env_mode(db: Session):
    """Run using environment variables."""
    email = os.getenv("SUPER_ADMIN_EMAIL", "admin@unifiedlayer.io")
    username = os.getenv("SUPER_ADMIN_USERNAME", "superadmin")
    password = os.getenv("SUPER_ADMIN_PASSWORD", "changeme123")
    full_name = os.getenv("SUPER_ADMIN_FULLNAME", "Super Administrator")

    print("\n" + "="*60)
    print("🚀 SUPER ADMIN CREATION - ENVIRONMENT MODE")
    print("="*60 + "\n")

    if password == "changeme123":
        print("⚠️  WARNING: Using default password! Set SUPER_ADMIN_PASSWORD env var.")

    print(f"Creating Super Admin:")
    print(f"  Email: {email}")
    print(f"  Username: {username}")
    print(f"  Full Name: {full_name}\n")

    user = create_super_admin(email, username, password, full_name, db)

    if user:
        print("\n" + "="*60)
        print("✅ SUPER ADMIN CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"\nCredentials:")
        print(f"  Email: {email}")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
        print("="*60 + "\n")


def main():
    """Main function"""
    db = get_db_session()

    try:
        # Check if we should run in interactive or env mode
        if len(sys.argv) > 1 and sys.argv[1] == "--env":
            env_mode(db)
        else:
            interactive_mode(db)

    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user (Ctrl+C)")
        db.rollback()
    except Exception as e:
        print(f"\n❌ Error creating super admin: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
