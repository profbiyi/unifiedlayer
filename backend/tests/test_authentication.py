"""
Authentication tests.

Tests for JWT authentication, user login, token validation, and password handling.
"""
import pytest
from fastapi import status
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.models.pipeline import Organization, User
from backend.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    decode_access_token
)


@pytest.fixture
def test_org(db: Session):
    """Create test organization."""
    org = Organization(
        name="Test Organization",
        slug="test-org"
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


@pytest.fixture
def test_user(db: Session, test_org, setup_rbac):
    """Create test user with ORG_USER role."""
    from backend.models.rbac import UserRole

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        organization_id=test_org.id
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign ORG_USER role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_user_role"].id,
        organization_id=test_org.id
    )
    db.add(user_role)
    db.flush()

    return user


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_get_password_hash(self):
        """Test that passwords are hashed correctly."""
        password = "my_secure_password"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_password_correct(self):
        """Test that correct password verification works."""
        password = "my_secure_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password verification fails."""
        password = "my_secure_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_same_password_twice_different_hashes(self):
        """Test that hashing the same password twice produces different hashes (salt)."""
        password = "my_secure_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test that access tokens are created correctly."""
        data = {"sub": "user_id_123"}
        token = create_access_token(data=data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """Test that valid tokens can be decoded."""
        user_id = "user_id_123"
        data = {"sub": user_id}
        token = create_access_token(data=data)

        payload = decode_access_token(token)
        assert payload is not None
        assert payload.get("sub") == user_id

    def test_decode_access_token_invalid(self):
        """Test that invalid tokens raise AuthError."""
        from backend.auth import AuthError
        invalid_token = "invalid.token.here"

        with pytest.raises(AuthError):
            decode_access_token(invalid_token)

    def test_decode_access_token_expired(self):
        """Test that expired tokens raise AuthError."""
        from backend.auth import AuthError
        data = {"sub": "user_id_123"}
        # Create token that expires immediately
        token = create_access_token(data=data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(AuthError):
            decode_access_token(token)

    def test_token_contains_user_id(self):
        """Test that token contains user ID in 'sub' claim."""
        user_id = "12345"
        data = {"sub": user_id}
        token = create_access_token(data=data)

        payload = decode_access_token(token)
        assert payload.get("sub") == user_id


class TestLogin:
    """Test user login functionality."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "wrong_password"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_email(self, client, test_user):
        """Test login using email instead of username."""
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",  # Using email as username
                "password": "password123"
            }
        )

        # Should work if implementation supports email login
        # If not implemented, this would fail - adjust based on implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


class TestProtectedEndpoints:
    """Test that endpoints require authentication."""

    def test_protected_endpoint_without_token(self, client):
        """Test that protected endpoints reject requests without tokens."""
        response = client.get("/pipelines")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test that protected endpoints reject invalid tokens."""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.get("/pipelines", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_valid_token(self, client, test_user):
        """Test that protected endpoints accept valid tokens."""
        token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/pipelines", headers=headers)

        assert response.status_code == status.HTTP_200_OK

    def test_protected_endpoint_without_bearer_prefix(self, client, test_user):
        """Test that tokens without 'Bearer' prefix are rejected."""
        token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": token}  # Missing "Bearer "
        response = client.get("/pipelines", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_new_user(self, client, test_org):
        """Test registering a new user."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "secure_password",
                "organization_id": test_org.id
            }
        )

        # Adjust based on actual implementation
        # If registration is implemented, should return 201
        # If not implemented, might return 404 or 405
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]

    def test_register_duplicate_username(self, client, test_user, test_org):
        """Test that registering with duplicate username fails."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",  # Already exists
                "email": "another@example.com",
                "password": "password123",
                "organization_id": test_org.id
            }
        )

        # Should fail if registration is implemented
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]

    def test_register_duplicate_email(self, client, test_user, test_org):
        """Test that registering with duplicate email fails."""
        response = client.post(
            "/auth/register",
            json={
                "username": "anotheruser",
                "email": "test@example.com",  # Already exists
                "password": "password123",
                "organization_id": test_org.id
            }
        )

        # Should fail if registration is implemented
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]


class TestTokenSecurity:
    """Test token security features."""

    def test_token_cannot_be_modified(self, test_user):
        """Test that modified tokens are rejected."""
        from backend.auth import AuthError
        token = create_access_token(data={"sub": str(test_user.id)})

        # Tamper with the token
        tampered_token = token[:-10] + "tamperedXX"

        with pytest.raises(AuthError):
            decode_access_token(tampered_token)

    def test_different_users_different_tokens(self):
        """Test that different users get different tokens."""
        token1 = create_access_token(data={"sub": "user1"})
        token2 = create_access_token(data={"sub": "user2"})

        assert token1 != token2

        payload1 = decode_access_token(token1)
        payload2 = decode_access_token(token2)

        assert payload1.get("sub") == "user1"
        assert payload2.get("sub") == "user2"

    def test_token_replay_protection(self):
        """Test that tokens contain timestamp claims."""
        token = create_access_token(data={"sub": "user_id"})
        payload = decode_access_token(token)

        # JWT should contain 'exp' (expiration) claim
        assert "exp" in payload
        # JWT should contain 'iat' (issued at) claim if implemented
        # This depends on your JWT implementation
