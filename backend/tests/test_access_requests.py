"""
Tests for the public access-request endpoint (gated trial funnel).
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.access_request import AccessRequest, AccessRequestStatus


VALID_PAYLOAD = {
    "company_name": "Acme Payments Ltd",
    "contact_name": "Ada Obi",
    "email": "ada@acmepayments.com",
    "country": "Nigeria",
    "sector": "digital_payments",
    "company_size": "11-50",
    "digital_systems": ["Paystack", "Spreadsheets (Excel, Google Sheets)"],
    "data_problem": "Transactions live in Paystack and accounts in spreadsheets; reconciling them takes days.",
}


class TestSubmitAccessRequest:
    def test_submit_creates_request(self, client: TestClient, db: Session):
        response = client.post("/access-requests", json=VALID_PAYLOAD)
        assert response.status_code == 201

        stored = db.query(AccessRequest).filter(
            AccessRequest.email == "ada@acmepayments.com"
        ).first()
        assert stored is not None
        assert stored.company_name == "Acme Payments Ltd"
        assert stored.status == AccessRequestStatus.NEW
        assert stored.digital_systems == VALID_PAYLOAD["digital_systems"]
        assert stored.research_consent is False  # not sent -> defaults false

    def test_research_consent_is_stored(self, client: TestClient, db: Session):
        payload = {
            **VALID_PAYLOAD,
            "email": "consenting@acmepayments.com",
            "research_consent": True,
        }
        response = client.post("/access-requests", json=payload)
        assert response.status_code == 201

        stored = db.query(AccessRequest).filter(
            AccessRequest.email == "consenting@acmepayments.com"
        ).first()
        assert stored.research_consent is True

    def test_submit_requires_valid_email(self, client: TestClient):
        payload = {**VALID_PAYLOAD, "email": "not-an-email"}
        response = client.post("/access-requests", json=payload)
        assert response.status_code == 422

    def test_submit_requires_data_problem(self, client: TestClient):
        payload = {**VALID_PAYLOAD, "data_problem": "short"}
        response = client.post("/access-requests", json=payload)
        assert response.status_code == 422

    def test_duplicate_pending_email_does_not_create_second_row(
        self, client: TestClient, db: Session
    ):
        first = client.post("/access-requests", json=VALID_PAYLOAD)
        assert first.status_code == 201
        second = client.post("/access-requests", json=VALID_PAYLOAD)
        assert second.status_code == 201

        count = db.query(AccessRequest).filter(
            AccessRequest.email == "ada@acmepayments.com"
        ).count()
        assert count == 1


class TestListAccessRequests:
    def test_list_requires_auth(self, client: TestClient):
        response = client.get("/access-requests")
        assert response.status_code == 401

    def test_regular_user_cannot_list(self, auth_client: TestClient):
        response = auth_client.get("/access-requests")
        assert response.status_code == 403

    def test_super_admin_can_list(self, super_admin_client: TestClient):
        submit = super_admin_client.post("/access-requests", json=VALID_PAYLOAD)
        assert submit.status_code == 201

        response = super_admin_client.get("/access-requests")
        assert response.status_code == 200
        emails = [r["email"] for r in response.json()]
        assert "ada@acmepayments.com" in emails


class TestUpdateAccessRequest:
    def test_super_admin_can_update_status(
        self, super_admin_client: TestClient, db: Session
    ):
        submit = super_admin_client.post("/access-requests", json=VALID_PAYLOAD)
        assert submit.status_code == 201
        request_id = db.query(AccessRequest).filter(
            AccessRequest.email == "ada@acmepayments.com"
        ).first().id

        response = super_admin_client.patch(
            f"/access-requests/{request_id}",
            json={"status": "qualified", "notes": "Discovery call went well."},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "qualified"
        assert body["notes"] == "Discovery call went well."

    def test_update_missing_request_returns_404(self, super_admin_client: TestClient):
        response = super_admin_client.patch(
            "/access-requests/999999", json={"status": "contacted"}
        )
        assert response.status_code == 404
