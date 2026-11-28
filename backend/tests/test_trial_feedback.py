"""
Tests for the post-trial feedback questionnaire and testimonial publishing.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.trial_feedback import (
    TrialFeedback,
    TestimonialStatus,
)


VALID = {
    "email": "Ada@AcmePayments.com",
    "respondent_name": "Ada Obi",
    "role": "Head of Finance",
    "company_name": "Acme Payments Ltd",
    "problem_relevance": 5,
    "hardest_systems": "Paystack and our Excel ledgers.",
    "biggest_concern": "Data security sign-off.",
    "continue_likelihood": 4,
    "top_feature": "local_connectors",
    "top_feature_reason": "We live on Paystack and MoMo.",
    "local_storage_importance": 5,
    "price_band": "ngn_25k_75k",
    "nps": 9,
    "research_consent": True,
    "quote_consent": True,
}


def _submit(client, **over):
    return client.post("/trial-feedback", json={**VALID, **over})


class TestSubmit:
    def test_submit_without_testimonial(self, client: TestClient, db: Session):
        r = _submit(client)
        assert r.status_code == 201
        fb = db.query(TrialFeedback).one()
        assert fb.email == "ada@acmepayments.com"
        assert fb.nps == 9
        assert fb.problem_relevance == 5
        assert fb.top_feature == "local_connectors"
        assert fb.price_band == "ngn_25k_75k"
        assert fb.quote_consent is True
        assert fb.testimonial_status == TestimonialStatus.NONE

    def test_price_other_kept_only_with_other_band(self, client: TestClient, db: Session):
        _submit(client, price_band="other", price_other="KES 5,000")
        assert db.query(TrialFeedback).one().price_other == "KES 5,000"

    def test_unknown_options_rejected(self, client: TestClient):
        assert _submit(client, top_feature="teleport").status_code == 422
        assert _submit(client, price_band="free_forever").status_code == 422

    def test_rating_bounds(self, client: TestClient):
        assert _submit(client, nps=11).status_code == 422
        assert _submit(client, problem_relevance=0).status_code == 422
        assert _submit(client, local_storage_importance=6).status_code == 422

    def test_testimonial_without_consent_is_never_publishable(self, client: TestClient, db: Session):
        _submit(client, testimonial="Great product", testimonial_consent=False)
        fb = db.query(TrialFeedback).one()
        assert fb.testimonial_consent is False
        assert fb.testimonial_status == TestimonialStatus.NONE

    def test_testimonial_with_consent_goes_pending(self, client: TestClient, db: Session):
        _submit(client, testimonial="Great product", testimonial_consent=True)
        fb = db.query(TrialFeedback).one()
        assert fb.testimonial_status == TestimonialStatus.PENDING

    def test_full_attribution_requires_details(self, client: TestClient):
        r = _submit(
            client,
            company_name="",
            testimonial="Great",
            testimonial_consent=True,
            testimonial_attribution="full",
        )
        assert r.status_code == 422


class TestModerationAndPublicFeed:
    def test_public_feed_only_shows_approved(
        self, client: TestClient, super_admin_client: TestClient, db: Session
    ):
        _submit(
            client,
            testimonial="Cut our month-end from days to hours.",
            testimonial_consent=True,
            testimonial_attribution="role_company_type",
        )
        fb = db.query(TrialFeedback).one()
        assert client.get("/trial-feedback/testimonials").json() == []

        r = super_admin_client.patch(
            f"/trial-feedback/{fb.id}", json={"testimonial_status": "approved"}
        )
        assert r.status_code == 200
        feed = client.get("/trial-feedback/testimonials").json()
        assert feed[0]["quote"] == "Cut our month-end from days to hours."
        assert feed[0]["attribution"] == "Head of Finance, fintech company"
        assert "email" not in feed[0]

    def test_cannot_approve_without_consent(self, client: TestClient, super_admin_client: TestClient, db: Session):
        _submit(client, testimonial="Nice", testimonial_consent=False)
        fb = db.query(TrialFeedback).one()
        r = super_admin_client.patch(f"/trial-feedback/{fb.id}", json={"testimonial_status": "approved"})
        assert r.status_code == 400

    def test_list_requires_auth(self, client: TestClient):
        assert client.get("/trial-feedback").status_code == 401

    def test_regular_user_cannot_list(self, auth_client: TestClient):
        assert auth_client.get("/trial-feedback").status_code == 403

    def test_export_is_anonymised(self, client: TestClient, super_admin_client: TestClient, db: Session):
        _submit(client)
        fb = db.query(TrialFeedback).one()
        super_admin_client.patch(
            f"/trial-feedback/{fb.id}",
            json={"participant_label": "P1", "sector_label": "Digital payments", "size_label": "11-50"},
        )
        r = super_admin_client.get("/trial-feedback/export.csv")
        assert r.status_code == 200
        body = r.text
        assert "P1" in body
        assert "Digital payments" in body
        assert "ada@acmepayments.com" not in body
        assert "Acme Payments" not in body
        assert "Ada Obi" not in body
