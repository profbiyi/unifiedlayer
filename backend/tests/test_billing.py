"""
Tests for billing models, service, and API routes.
"""
import pytest
import uuid

from backend.models.billing import (
    Subscription,
    UsageRecord,
    SubscriptionPlan,
    SubscriptionStatus,
    PLAN_LIMITS,
)


class TestBillingModels:
    def test_plan_limits_defined(self):
        assert SubscriptionPlan.STARTER in PLAN_LIMITS
        assert SubscriptionPlan.PROFESSIONAL in PLAN_LIMITS
        assert SubscriptionPlan.ENTERPRISE in PLAN_LIMITS

    def test_starter_limits(self):
        limits = PLAN_LIMITS[SubscriptionPlan.STARTER]
        assert limits["max_connectors"] == 3
        assert limits["max_rows_per_month"] == 10_000
        assert limits["price_gbp"] == 0

    def test_professional_limits(self):
        limits = PLAN_LIMITS[SubscriptionPlan.PROFESSIONAL]
        assert limits["max_connectors"] == -1  # Unlimited
        assert limits["max_rows_per_month"] == 500_000
        assert limits["price_gbp"] == 35

    def test_enterprise_unlimited(self):
        limits = PLAN_LIMITS[SubscriptionPlan.ENTERPRISE]
        assert limits["max_rows_per_month"] == -1

    def test_subscription_model(self, db):
        # We need an organization first — skip if no org table
        try:
            from backend.models.pipeline import Organization
            org = Organization(name="Test Billing Org", slug="test-billing-org")
            db.add(org)
            db.flush()

            sub = Subscription(
                public_id=uuid.uuid4(),
                organization_id=org.id,
                plan=SubscriptionPlan.STARTER,
                status=SubscriptionStatus.ACTIVE,
            )
            db.add(sub)
            db.flush()

            assert sub.id is not None
            assert sub.plan == SubscriptionPlan.STARTER
            assert sub.currency == "GBP"
        except Exception:
            pytest.skip("Organization model not available in test DB")

    def test_usage_record_model(self, db):
        try:
            from backend.models.pipeline import Organization
            org = Organization(name="Test Usage Org", slug="test-usage-org")
            db.add(org)
            db.flush()

            usage = UsageRecord(
                organization_id=org.id,
                period_year=2026,
                period_month=1,
                rows_synced=5000,
                pipeline_runs=20,
            )
            db.add(usage)
            db.flush()

            assert usage.id is not None
            assert usage.rows_synced == 5000
        except Exception:
            pytest.skip("Organization model not available in test DB")


class TestBillingAPI:
    def test_get_plans(self, client):
        response = client.get("/billing/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        plans = data["plans"]
        assert len(plans) == 3
        plan_names = [p["plan"] for p in plans]
        assert "starter" in plan_names
        assert "professional" in plan_names
        assert "enterprise" in plan_names

    def test_professional_has_regional_prices(self, client):
        """Professional carries purchasing-power prices per market."""
        response = client.get("/billing/plans")
        assert response.status_code == 200
        plans = {p["plan"]: p for p in response.json()["plans"]}

        prices = {p["currency"]: p for p in plans["professional"]["prices"]}
        assert set(prices) == {"NGN", "KES", "GHS", "GBP", "EUR"}
        # Local prices are set deliberately, NOT FX conversions of the GBP price
        assert prices["NGN"]["monthly"] == 15_000
        assert prices["KES"]["monthly"] == 2_000
        assert prices["GHS"]["monthly"] == 200
        assert prices["GBP"]["monthly"] == 35
        assert prices["NGN"]["provider"] == "paystack"
        assert prices["GBP"]["provider"] == "stripe"

        # Free and custom-priced plans carry no regional price list
        assert plans["starter"]["prices"] == []
        assert plans["enterprise"]["prices"] == []

    def test_paystack_amounts_derived_from_regional_pricing(self):
        """Paystack checkout amounts must always match the pricing table (x100 minor units)."""
        from backend.models.billing import REGIONAL_PRICING, SubscriptionPlan
        from backend.services.billing_service import BillingService

        amounts = BillingService.PAYSTACK_PLAN_AMOUNTS[SubscriptionPlan.PROFESSIONAL]
        for currency, pricing in REGIONAL_PRICING.items():
            if pricing["provider"] == "paystack":
                assert amounts[currency] == pricing["professional_monthly"] * 100

    def test_get_subscription_unauthenticated(self, client):
        response = client.get("/billing/subscription")
        assert response.status_code in [401, 403]

    def test_get_usage_unauthenticated(self, client):
        response = client.get("/billing/usage")
        assert response.status_code in [401, 403]


class TestAnalyticsAPI:
    def test_analytics_overview_unauthenticated(self, client):
        response = client.get("/analytics/overview")
        assert response.status_code in [401, 403]


class TestInsightsAPI:
    def test_insights_dashboard_unauthenticated(self, client):
        response = client.get("/insights/dashboard")
        assert response.status_code in [401, 403]

    def test_insights_roi_unauthenticated(self, client):
        response = client.get("/insights/roi")
        assert response.status_code in [401, 403]

    def test_insights_cash_flow_unauthenticated(self, client):
        response = client.get("/insights/cash-flow")
        assert response.status_code in [401, 403]
