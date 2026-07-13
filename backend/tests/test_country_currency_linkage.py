"""
Tests for the country → billing currency linkage (purchasing-power pricing).

An organization's country decides which market price it gets at onboarding;
the super admin can change the currency later, but only to a deliberately
priced market — never an arbitrary/FX-converted one.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import Organization
from backend.models.billing import Subscription, currency_for_country


def org_payload(slug: str, country=None) -> dict:
    payload = {
        "name": f"Test Org {slug}",
        "slug": slug,
        "subscription_plan": "professional",
        "admin_email": f"admin@{slug}.example.com",
        "admin_username": f"admin_{slug.replace('-', '_')}",
        "admin_password": "SecurePass123!",
    }
    if country is not None:
        payload["country"] = country
    return payload


class TestCurrencyForCountry:
    def test_deliberately_priced_markets(self):
        assert currency_for_country("Nigeria") == "NGN"
        assert currency_for_country("kenya") == "KES"
        assert currency_for_country("Ghana") == "GHS"
        assert currency_for_country("United Kingdom") == "GBP"
        assert currency_for_country("France") == "EUR"

    def test_unknown_or_missing_country_defaults_to_gbp(self):
        assert currency_for_country(None) == "GBP"
        assert currency_for_country("Atlantis") == "GBP"


class TestOrgCreationCurrencyLinkage:
    def test_nigerian_org_billed_in_ngn(self, super_admin_client: TestClient, db: Session):
        response = super_admin_client.post(
            "/admin/organizations", json=org_payload("naija-fintech", "Nigeria")
        )
        assert response.status_code == 200, response.text

        org = db.query(Organization).filter(Organization.slug == "naija-fintech").first()
        assert org.country == "Nigeria"
        sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
        assert sub is not None
        assert sub.currency == "NGN"

    def test_org_without_country_defaults_to_gbp(self, super_admin_client: TestClient, db: Session):
        response = super_admin_client.post(
            "/admin/organizations", json=org_payload("no-country-org")
        )
        assert response.status_code == 200, response.text

        org = db.query(Organization).filter(Organization.slug == "no-country-org").first()
        sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
        assert sub.currency == "GBP"


class TestBillingCurrencyUpdate:
    def _create_org(self, super_admin_client: TestClient, db: Session, slug: str, country: str):
        response = super_admin_client.post(
            "/admin/organizations", json=org_payload(slug, country)
        )
        assert response.status_code == 200, response.text
        return db.query(Organization).filter(Organization.slug == slug).first()

    def test_super_admin_can_change_currency(self, super_admin_client: TestClient, db: Session):
        org = self._create_org(super_admin_client, db, "moving-org", "United Kingdom")

        response = super_admin_client.patch(
            f"/admin/organizations/{org.id}/billing-currency",
            json={"currency": "kes"},  # case-insensitive
        )
        assert response.status_code == 200
        assert response.json()["currency"] == "KES"

        sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
        assert sub.currency == "KES"

    def test_unsupported_currency_rejected(self, super_admin_client: TestClient, db: Session):
        org = self._create_org(super_admin_client, db, "usd-wannabe", "Nigeria")

        response = super_admin_client.patch(
            f"/admin/organizations/{org.id}/billing-currency",
            json={"currency": "USD"},
        )
        assert response.status_code == 400

        sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
        assert sub.currency == "NGN"  # unchanged

    def test_regular_user_cannot_change_currency(self, auth_client: TestClient):
        response = auth_client.patch(
            "/admin/organizations/1/billing-currency", json={"currency": "NGN"}
        )
        assert response.status_code == 403

    def test_missing_org_returns_404(self, super_admin_client: TestClient):
        response = super_admin_client.patch(
            "/admin/organizations/999999/billing-currency", json={"currency": "NGN"}
        )
        assert response.status_code == 404
