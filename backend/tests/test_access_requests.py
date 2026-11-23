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


class TestDeleteAccessRequest:
    def test_super_admin_can_delete(self, super_admin_client: TestClient, db: Session):
        submit = super_admin_client.post("/access-requests", json=VALID_PAYLOAD)
        assert submit.status_code == 201
        request_id = db.query(AccessRequest).filter(
            AccessRequest.email == "ada@acmepayments.com"
        ).first().id

        response = super_admin_client.delete(f"/access-requests/{request_id}")
        assert response.status_code == 204
        assert (
            db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
            is None
        )

    def test_regular_user_cannot_delete(self, auth_client: TestClient):
        response = auth_client.delete("/access-requests/1")
        assert response.status_code == 403

    def test_delete_missing_request_returns_404(self, super_admin_client: TestClient):
        response = super_admin_client.delete("/access-requests/999999")
        assert response.status_code == 404


class TestOnboardAccessRequest:
    def _submit(self, client: TestClient, db: Session) -> int:
        # The public submit endpoint returns only a message; the row id comes
        # from the DB (mirrors the other tests in this file).
        resp = client.post("/access-requests", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        req = (
            db.query(AccessRequest)
            .filter(AccessRequest.email == VALID_PAYLOAD["email"])
            .order_by(AccessRequest.id.desc())
            .first()
        )
        return req.id

    def test_onboard_provisions_org_and_admin(self, super_admin_client: TestClient, db: Session):
        request_id = self._submit(super_admin_client, db)

        resp = super_admin_client.post(
            f"/access-requests/{request_id}/onboard",
            json={"subscription_plan": "professional"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["admin_email"] == VALID_PAYLOAD["email"]
        assert body["temporary_password"]
        assert body["organization_slug"]

        # the request advanced to trial_active and is marked onboarded
        req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
        db.refresh(req)
        assert req.status == AccessRequestStatus.TRIAL_ACTIVE
        assert req.onboarded_at is not None
        assert req.onboarded_organization_id == body["organization_id"]

        # a real admin user now exists for that email, as ORG_ADMIN
        from backend.models import User
        user = db.query(User).filter(User.email == VALID_PAYLOAD["email"]).first()
        assert user is not None
        assert user.organization_id == body["organization_id"]
        assert "org_admin" in {ur.role.slug for ur in user.user_roles}

    def test_onboard_twice_conflicts(self, super_admin_client: TestClient, db: Session):
        request_id = self._submit(super_admin_client, db)
        first = super_admin_client.post(f"/access-requests/{request_id}/onboard", json={})
        assert first.status_code == 200
        second = super_admin_client.post(f"/access-requests/{request_id}/onboard", json={})
        assert second.status_code == 409

    def test_onboard_requires_super_admin(self, auth_client: TestClient):
        resp = auth_client.post("/access-requests/1/onboard", json={})
        assert resp.status_code == 403

    def test_onboard_missing_request_404(self, super_admin_client: TestClient):
        resp = super_admin_client.post("/access-requests/999999/onboard", json={})
        assert resp.status_code == 404

    def test_force_delete_org_reenables_onboarding(
        self, super_admin_client: TestClient, db: Session
    ):
        # onboard -> request is marked onboarded into the new org
        request_id = self._submit(super_admin_client, db)
        onboard = super_admin_client.post(
            f"/access-requests/{request_id}/onboard", json={}
        )
        assert onboard.status_code == 200
        org_id = onboard.json()["organization_id"]

        # force-delete the org (cascades users; clears the request's onboarded marker)
        force = super_admin_client.request(
            "DELETE",
            f"/admin/organizations/{org_id}/force",
            json={"reason": "test cleanup"},
        )
        assert force.status_code == 200, force.text

        req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
        db.refresh(req)
        assert req.onboarded_at is None
        assert req.onboarded_organization_id is None

        # and the email is free, so they can be onboarded again
        again = super_admin_client.post(
            f"/access-requests/{request_id}/onboard", json={}
        )
        assert again.status_code == 200

    def test_force_delete_org_with_related_rows(
        self, super_admin_client: TestClient, db: Session
    ):
        """Force-delete must succeed for a fully-populated org.

        Regression: many models back-reference Organization/User/Pipeline with a
        NOT-NULL FK and no passive_deletes, so deleting the org made the ORM try
        to NULL those NOT-NULL FKs -> 500. This seeds the whole graph
        (onboarding, AI, source, destination, pipeline, column lineage) and
        asserts the force-delete cascades cleanly.
        """
        from backend.models import User
        from backend.models.pipeline import (
            DataSource,
            Destination,
            Pipeline,
            SourceType,
            DestinationType,
        )
        from backend.models.onboarding import OnboardingProgress
        from backend.models.ai import AIConversation
        from backend.models.column_lineage import ColumnLineage

        request_id = self._submit(super_admin_client, db)
        onboard = super_admin_client.post(
            f"/access-requests/{request_id}/onboard", json={}
        )
        assert onboard.status_code == 200
        org_id = onboard.json()["organization_id"]

        user = db.query(User).filter(User.email == VALID_PAYLOAD["email"]).first()
        assert user is not None

        # user/org-scoped children with NOT-NULL FKs
        db.add(OnboardingProgress(user_id=user.id, organization_id=org_id))
        db.add(
            AIConversation(
                organization_id=org_id, user_id=user.id, title="Regression seed"
            )
        )

        # a full source -> destination -> pipeline chain (the common real case)
        src = DataSource(
            organization_id=org_id,
            name="Seed source",
            source_type=SourceType.POSTGRES,
            config={},
        )
        dst = Destination(
            organization_id=org_id,
            name="Seed dest",
            destination_type=DestinationType.POSTGRES,
            config={},
        )
        db.add_all([src, dst])
        db.flush()
        pipe = Pipeline(
            organization_id=org_id,
            source_id=src.id,
            destination_id=dst.id,
            name="Seed pipeline",
        )
        db.add(pipe)
        db.add(
            ColumnLineage(
                organization_id=org_id,
                source_table="a",
                source_column="b",
                target_table="c",
                target_column="d",
            )
        )
        db.commit()

        force = super_admin_client.request(
            "DELETE",
            f"/admin/organizations/{org_id}/force",
            json={"reason": "regression: full graph"},
        )
        assert force.status_code == 200, force.text

        # org and every seeded child are gone (DB ON DELETE CASCADE).
        assert (
            db.query(OnboardingProgress)
            .filter(OnboardingProgress.organization_id == org_id)
            .count()
            == 0
        )
        assert (
            db.query(AIConversation)
            .filter(AIConversation.organization_id == org_id)
            .count()
            == 0
        )
        assert db.query(Pipeline).filter(Pipeline.organization_id == org_id).count() == 0
        assert db.query(DataSource).filter(DataSource.organization_id == org_id).count() == 0
        assert (
            db.query(ColumnLineage)
            .filter(ColumnLineage.organization_id == org_id)
            .count()
            == 0
        )
