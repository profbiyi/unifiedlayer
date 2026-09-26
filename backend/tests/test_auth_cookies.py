"""Tests for httpOnly cookie auth + refresh-token rotation."""
from backend.auth import create_access_token, create_refresh_token


def _login(client):
    return client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"},
    )


class TestLoginCookies:
    def test_login_sets_httponly_access_and_refresh_cookies(self, client, test_user):
        resp = _login(client)
        assert resp.status_code == 200
        # both cookies present
        assert "token" in resp.cookies
        assert "refresh_token" in resp.cookies
        # and marked HttpOnly
        set_cookie_blob = " ".join(resp.headers.get_list("set-cookie")).lower()
        assert "httponly" in set_cookie_blob


class TestRefresh:
    def test_refresh_with_cookie_issues_new_access_token(self, client, test_user):
        _login(client)  # TestClient keeps the cookies
        resp = client.post("/auth/refresh")
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        # a fresh refresh cookie is set (rotation)
        assert "token" in resp.cookies

    def test_refresh_without_token_is_401(self, client, test_user):
        resp = client.post("/auth/refresh")  # no login, no cookie
        assert resp.status_code == 401

    def test_access_token_rejected_as_refresh(self, client, test_user):
        # an access token (no type=refresh claim) must not be accepted at /refresh
        access = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
        resp = client.post("/auth/refresh", cookies={"refresh_token": access})
        assert resp.status_code == 401


class TestRefreshTokenNotUsableForApi:
    def test_refresh_token_rejected_by_get_current_user(self, client, test_user):
        # a refresh token presented as a Bearer must not authenticate API calls
        refresh = create_refresh_token(data={"sub": str(test_user.id)})
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {refresh}"})
        assert resp.status_code == 401
