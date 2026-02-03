"""Tests for email verification and resend-verification endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes.auth import router


def _make_app(db_session, current_user=None):
    app = FastAPI()
    app.include_router(router)

    from backend.database import get_db
    from backend.auth import get_current_user

    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user

    return app


@pytest.fixture
def mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# verify-email
# ---------------------------------------------------------------------------

class TestVerifyEmailValidToken:
    def test_verify_email_valid_token(self, mock_db):
        user = MagicMock()
        user.email_verified = False
        user.email_verification_token = "valid-token"

        mock_db.query.return_value.filter.return_value.first.return_value = user

        app = _make_app(mock_db)
        client = TestClient(app)

        resp = client.post("/auth/verify-email", json={"token": "valid-token"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email verified successfully"
        assert user.email_verified is True
        assert user.email_verification_token is None
        mock_db.commit.assert_called_once()


class TestVerifyEmailInvalidToken:
    def test_verify_email_invalid_token(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app = _make_app(mock_db)
        client = TestClient(app)

        resp = client.post("/auth/verify-email", json={"token": "bad-token"})
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# resend-verification
# ---------------------------------------------------------------------------

class TestResendVerification:
    @patch("backend.api.routes.auth.send_verification_email")
    def test_resend_verification(self, mock_send, mock_db):
        user = MagicMock()
        user.email = "user@example.com"
        user.email_verified = False

        mock_db.query.return_value.filter.return_value.first.return_value = user

        app = _make_app(mock_db)
        client = TestClient(app)

        resp = client.post("/auth/resend-verification", json={"email": "user@example.com"})
        assert resp.status_code == 200
        mock_send.assert_called_once()
        # A new token should have been set
        assert user.email_verification_token is not None
        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# register sends verification email
# ---------------------------------------------------------------------------

class TestRegisterSendsVerificationEmail:
    @patch("backend.api.routes.auth.send_verification_email")
    @patch("backend.api.routes.auth.get_password_hash", return_value="hashed")
    def test_register_sends_verification_email(self, mock_hash, mock_send, mock_db):
        # No existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def _refresh(obj):
            obj.id = 1
            obj.public_id = "uuid-1"
            obj.created_at = "2025-01-01"
            obj.updated_at = "2025-01-01"
            obj.last_login = None

        mock_db.refresh = _refresh

        app = _make_app(mock_db)
        client = TestClient(app)

        resp = client.post("/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "securepassword123",
            "organization_id": 1,
        })
        assert resp.status_code == 201
        mock_send.assert_called_once()
        # First arg is the email
        assert mock_send.call_args[0][0] == "new@example.com"
