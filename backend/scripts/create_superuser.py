"""
Create Super User Script.

Creates a super admin user with global access to all organizations.
"""

import sys
from pathlib import Path
import getpass
import uuid
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from backend.database import get_db_session
from backend.models import Organization, User
from backend.models.rbac import Role, UserRole
from backend.auth import get_password_hash


def create_superuser(
    email: str,
    username: str,
    password: str,
    full_name: str,
    db: Session,
) -> User:
    """
    Create a super admin user.

    Args:
        email: User email
        username: Username
        password: Password
        full_name: Full name
        db: Database session

    Returns:
        Created user
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"\n❌ Error: User with email '{email}' already exists!")
        print(f"   User ID: {existing_user.id}")
        print(f"   Username: {existing_user.username}")
        sys.exit(1)

    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"\n❌ Error: User with username '{username}' already exists!")
        print(f"   Email: {existing_user.email}")
        sys.exit(1)

    # Get or create a platform organization for super admins
    platform_org = db.query(Organization).filter(
        Organization.slug == "platform-admin"
    ).first()

    if not platform_org:
        platform_org = Organization(
            name="Platform Administration",
            slug="platform-admin",
            subscription_plan="enterprise",
            max_users=1000,
            is_active=True,
            can_sync_data=True,
            admin_onboarded=True,
            admin_onboarded_at=datetime.now(timezone.utc),
        )
        db.add(platform_org)
        db.commit()
        db.refresh(platform_org)
        print(f"✅ Created platform organization: {platform_org.name}")

    # Create user
    user = User(
        public_id=uuid.uuid4(),
        organization_id=platform_org.id,
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=True,  # Legacy field
        email_verified=True,
        invitation_status="accepted",
        invitation_accepted_at=datetime.now(timezone.utc),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"✅ Created user: {user.email}")

    # Assign SUPER_ADMIN role
    super_admin_role = db.query(Role).filter(Role.slug == "super_admin").first()

    if not super_admin_role:
        print("\n❌ Error: SUPER_ADMIN role not found!")
        print("   Run: python backend/scripts/seed_rbac.py")
        db.delete(user)
        db.commit()
        sys.exit(1)

    user_role = UserRole(
        user_id=user.id,
        role_id=super_admin_role.id,
        organization_id=platform_org.id,
        granted_by_id=user.id,  # Self-granted
    )

    db.add(user_role)
    db.commit()

    print(f"✅ Assigned SUPER_ADMIN role to user")

    return user


def main():
    """Main function."""
    print("\n" + "="*60)
    print("🔑 CREATE SUPER USER")
    print("="*60 + "\n")

    # Get user input
    email = input("Email: ").strip()
    username = input("Username: ").strip()
    full_name = input("Full Name: ").strip()
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")

    # Validate input
    if not email or not username or not password:
        print("\n❌ Error: Email, username, and password are required!")
        sys.exit(1)

    if password != password_confirm:
        print("\n❌ Error: Passwords do not match!")
        sys.exit(1)

    if len(password) < 8:
        print("\n❌ Error: Password must be at least 8 characters!")
        sys.exit(1)

    # Validate email format
    if "@" not in email or "." not in email:
        print("\n❌ Error: Invalid email format!")
        sys.exit(1)

    print("\n" + "="*60)
    print("Creating super user with:")
    print(f"  Email: {email}")
    print(f"  Username: {username}")
    print(f"  Full Name: {full_name or '(not provided)'}")
    print("="*60 + "\n")

    db = get_db_session()

    try:
        user = create_superuser(
            email=email,
            username=username,
            password=password,
            full_name=full_name or username,
            db=db,
        )

        print("\n" + "="*60)
        print("✅ SUPER USER CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📧 Email: {user.email}")
        print(f"👤 Username: {user.username}")
        print(f"🆔 User ID: {user.public_id}")
        print(f"🏢 Organization: {user.organization.name}")
        print(f"🔑 Role: SUPER_ADMIN (global access)")
        print("\n💡 You can now login with these credentials!")
        print("   Frontend: http://localhost")
        print("   API Docs: http://localhost/docs")
        print("\n" + "="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Error creating super user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
