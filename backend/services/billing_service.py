"""
Billing Service.

Handles Stripe integration, subscription management, usage metering,
and webhook processing.
"""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

import requests as http_requests
import stripe
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.billing import (
    Subscription,
    Invoice,
    UsageRecord,
    SubscriptionPlan,
    SubscriptionStatus,
    PaymentProvider,
    InvoiceStatus,
    PLAN_LIMITS,
    REGIONAL_PRICING,
)
from backend.models.pipeline import Organization, User

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)


class BillingService:
    """Manages subscriptions, payments, and usage metering."""

    # --- Stripe Customer Management ---

    @staticmethod
    def create_stripe_customer(db: Session, organization: Organization, user: User) -> str:
        """Create a Stripe customer for an organization."""
        customer = stripe.Customer.create(
            email=user.email,
            name=organization.name,
            metadata={
                "organization_id": str(organization.id),
                "organization_name": organization.name,
            },
        )

        # Update or create subscription record
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization.id
        ).first()

        if not sub:
            sub = Subscription(
                organization_id=organization.id,
                plan=SubscriptionPlan.STARTER,
                status=SubscriptionStatus.ACTIVE,
                payment_provider=PaymentProvider.STRIPE,
                stripe_customer_id=customer.id,
                currency="GBP",
                billing_email=user.email,
            )
            db.add(sub)
        else:
            sub.stripe_customer_id = customer.id
            sub.payment_provider = PaymentProvider.STRIPE

        db.commit()
        db.refresh(sub)
        return customer.id

    # --- Subscription Management ---

    @staticmethod
    def create_checkout_session(
        db: Session,
        organization: Organization,
        plan: SubscriptionPlan,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session for subscribing to a plan."""
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization.id
        ).first()

        if not sub or not sub.stripe_customer_id:
            raise ValueError("Organization must have a Stripe customer. Call create_stripe_customer first.")

        price_id = getattr(settings, f'STRIPE_PRICE_{plan.value.upper()}', None)
        if not price_id:
            raise ValueError(f"No Stripe price configured for plan: {plan.value}")

        session = stripe.checkout.Session.create(
            customer=sub.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "organization_id": str(organization.id),
                "plan": plan.value,
            },
            subscription_data={
                "metadata": {
                    "organization_id": str(organization.id),
                    "plan": plan.value,
                },
            },
        )

        return session.url

    @staticmethod
    def create_portal_session(db: Session, organization: Organization, return_url: str) -> str:
        """Create a Stripe Customer Portal session for managing billing."""
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization.id
        ).first()

        if not sub or not sub.stripe_customer_id:
            raise ValueError("No Stripe customer found for this organization.")

        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url,
        )

        return session.url

    @staticmethod
    def get_subscription(db: Session, organization_id: int) -> Optional[Subscription]:
        """Get subscription for an organization."""
        return db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).first()

    @staticmethod
    def get_plan_limits(plan: SubscriptionPlan) -> dict:
        """Get limits for a subscription plan."""
        return PLAN_LIMITS.get(plan, PLAN_LIMITS[SubscriptionPlan.STARTER])

    # --- Usage Metering ---

    @staticmethod
    def get_or_create_usage_record(db: Session, organization_id: int) -> UsageRecord:
        """Get or create usage record for the current month."""
        now = datetime.now(timezone.utc)
        record = db.query(UsageRecord).filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.period_year == now.year,
            UsageRecord.period_month == now.month,
        ).first()

        if not record:
            # Get plan limits
            sub = db.query(Subscription).filter(
                Subscription.organization_id == organization_id
            ).first()
            plan = sub.plan if sub else SubscriptionPlan.STARTER
            limits = PLAN_LIMITS[plan]

            record = UsageRecord(
                organization_id=organization_id,
                period_year=now.year,
                period_month=now.month,
                rows_limit=limits["max_rows_per_month"] if limits["max_rows_per_month"] > 0 else 999_999_999,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return record

    @staticmethod
    def record_rows_synced(db: Session, organization_id: int, rows: int) -> UsageRecord:
        """Record rows synced for usage metering."""
        record = BillingService.get_or_create_usage_record(db, organization_id)
        record.rows_synced += rows

        # Check if over limit
        if record.rows_limit > 0 and record.rows_synced > record.rows_limit:
            record.rows_overage = record.rows_synced - record.rows_limit

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def record_pipeline_run(db: Session, organization_id: int) -> UsageRecord:
        """Record a pipeline run for usage metering."""
        record = BillingService.get_or_create_usage_record(db, organization_id)
        record.pipeline_runs += 1
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def record_api_call(db: Session, organization_id: int) -> UsageRecord:
        """Record an API call for usage metering."""
        record = BillingService.get_or_create_usage_record(db, organization_id)
        record.api_calls += 1
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def check_usage_limit(db: Session, organization_id: int, metric: str = "rows_synced") -> dict:
        """Check if organization is within usage limits."""
        record = BillingService.get_or_create_usage_record(db, organization_id)
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).first()
        plan = sub.plan if sub else SubscriptionPlan.STARTER
        limits = PLAN_LIMITS[plan]

        if metric == "rows_synced":
            limit = limits["max_rows_per_month"]
            current = record.rows_synced
        elif metric == "connectors":
            limit = limits["max_connectors"]
            current = record.active_connectors
        elif metric == "pipelines":
            limit = limits["max_pipelines"]
            # Count active pipelines from DB
            from backend.models.pipeline import Pipeline
            current = db.query(Pipeline).filter(
                Pipeline.organization_id == organization_id,
                Pipeline.is_active,
            ).count()
        else:
            return {"allowed": True, "current": 0, "limit": -1}

        if limit == -1:  # Unlimited
            return {"allowed": True, "current": current, "limit": -1, "plan": plan.value}

        return {
            "allowed": current < limit,
            "current": current,
            "limit": limit,
            "usage_percent": round((current / limit) * 100, 1) if limit > 0 else 0,
            "plan": plan.value,
        }

    # --- Paystack Integration ---

    PAYSTACK_API_BASE = "https://api.paystack.co"
    PAYSTACK_SUPPORTED_CURRENCIES = {"NGN", "KES", "GHS"}

    # Amounts in the smallest currency unit (kobo/cents/pesewas), derived
    # from REGIONAL_PRICING — the purchasing-power pricing table in
    # backend/models/billing.py. Change prices there, not here.
    PAYSTACK_PLAN_AMOUNTS = {
        SubscriptionPlan.PROFESSIONAL: {
            currency: pricing["professional_monthly"] * 100
            for currency, pricing in REGIONAL_PRICING.items()
            if pricing["provider"] == "paystack"
        },
    }

    @staticmethod
    def _paystack_headers() -> dict:
        """Return authorization headers for Paystack API."""
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def create_paystack_customer(db: Session, organization: Organization, user: User) -> str:
        """Create a Paystack customer for an organization. Returns the customer code."""
        resp = http_requests.post(
            f"{BillingService.PAYSTACK_API_BASE}/customer",
            headers=BillingService._paystack_headers(),
            json={
                "email": user.email,
                "first_name": user.email.split("@")[0],
                "metadata": {
                    "organization_id": str(organization.id),
                    "organization_name": organization.name,
                },
            },
        )
        resp.raise_for_status()
        customer_code = resp.json()["data"]["customer_code"]

        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization.id
        ).first()

        if not sub:
            sub = Subscription(
                organization_id=organization.id,
                plan=SubscriptionPlan.STARTER,
                status=SubscriptionStatus.ACTIVE,
                payment_provider=PaymentProvider.PAYSTACK,
                paystack_customer_code=customer_code,
                currency="NGN",
                billing_email=user.email,
            )
            db.add(sub)
        else:
            sub.paystack_customer_code = customer_code
            sub.payment_provider = PaymentProvider.PAYSTACK

        db.commit()
        db.refresh(sub)
        return customer_code

    @staticmethod
    def create_paystack_checkout(
        plan: SubscriptionPlan,
        email: str,
        callback_url: str,
        currency: str = "NGN",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Initialize a Paystack transaction. Returns dict with authorization_url and reference.
        Amount is in the smallest currency unit (kobo for NGN).
        """
        currency = currency.upper()
        if currency not in BillingService.PAYSTACK_SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported Paystack currency: {currency}")

        amounts = BillingService.PAYSTACK_PLAN_AMOUNTS.get(plan)
        if not amounts or currency not in amounts:
            raise ValueError(f"No Paystack price configured for plan {plan.value} in {currency}")

        amount = amounts[currency]

        payload = {
            "email": email,
            "amount": amount,
            "currency": currency,
            "callback_url": callback_url,
            "metadata": metadata or {},
        }

        resp = http_requests.post(
            f"{BillingService.PAYSTACK_API_BASE}/transaction/initialize",
            headers=BillingService._paystack_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return {
            "authorization_url": data["authorization_url"],
            "access_code": data["access_code"],
            "reference": data["reference"],
        }

    @staticmethod
    def verify_paystack_transaction(reference: str) -> dict:
        """Verify a Paystack transaction by reference."""
        resp = http_requests.get(
            f"{BillingService.PAYSTACK_API_BASE}/transaction/verify/{reference}",
            headers=BillingService._paystack_headers(),
        )
        resp.raise_for_status()
        return resp.json()["data"]

    @staticmethod
    def handle_paystack_webhook(db: Session, payload: bytes, signature: str) -> None:
        """Verify and process a Paystack webhook event."""
        secret = settings.PAYSTACK_WEBHOOK_SECRET or settings.PAYSTACK_SECRET_KEY
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Paystack webhook signature")

        import json
        event = json.loads(payload)
        event_type = event.get("event", "")
        data = event.get("data", {})

        logger.info(f"Processing Paystack webhook: {event_type}")

        if event_type == "charge.success":
            BillingService._handle_paystack_charge_success(db, data)
        elif event_type in ("subscription.create", "subscription.enable"):
            BillingService._handle_paystack_subscription_active(db, data)
        elif event_type in ("subscription.disable", "subscription.expiring_cards"):
            BillingService._handle_paystack_subscription_cancelled(db, data)

    @staticmethod
    def _handle_paystack_charge_success(db: Session, data: dict) -> None:
        """Handle a successful Paystack charge."""
        email = data.get("customer", {}).get("email", "")
        metadata = data.get("metadata", {})
        org_id = metadata.get("organization_id")

        if not org_id:
            # Try to find org by billing email
            sub = db.query(Subscription).filter(Subscription.billing_email == email).first()
        else:
            sub = db.query(Subscription).filter(
                Subscription.organization_id == int(org_id)
            ).first()

        if not sub:
            logger.warning(f"Paystack charge.success: no subscription found for {email}")
            return

        plan_name = metadata.get("plan", "professional")
        sub.plan = SubscriptionPlan(plan_name)
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_start = datetime.now(timezone.utc)

        # Update organization
        org = db.query(Organization).filter(Organization.id == sub.organization_id).first()
        if org:
            limits = PLAN_LIMITS[sub.plan]
            org.subscription_plan = plan_name
            org.max_users = limits["max_users"] if limits["max_users"] > 0 else 999
            org.subscription_status = "active"

        # Create invoice record
        invoice = Invoice(
            subscription_id=sub.id,
            organization_id=sub.organization_id,
            paystack_reference=data.get("reference"),
            status=InvoiceStatus.PAID,
            currency=data.get("currency", "NGN").upper(),
            amount_due=data.get("amount", 0),
            amount_paid=data.get("amount", 0),
            amount_remaining=0,
            paid_at=datetime.now(timezone.utc),
        )
        db.add(invoice)
        db.commit()

    @staticmethod
    def _handle_paystack_subscription_active(db: Session, data: dict) -> None:
        """Handle Paystack subscription activation."""
        customer_code = data.get("customer", {}).get("customer_code", "")
        sub = db.query(Subscription).filter(
            Subscription.paystack_customer_code == customer_code
        ).first()

        if sub:
            sub.paystack_subscription_code = data.get("subscription_code")
            sub.status = SubscriptionStatus.ACTIVE
            db.commit()

    @staticmethod
    def _handle_paystack_subscription_cancelled(db: Session, data: dict) -> None:
        """Handle Paystack subscription cancellation."""
        subscription_code = data.get("subscription_code", "")
        sub = db.query(Subscription).filter(
            Subscription.paystack_subscription_code == subscription_code
        ).first()

        if sub:
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancelled_at = datetime.now(timezone.utc)
            sub.plan = SubscriptionPlan.STARTER
            db.commit()

    # --- Webhook Processing ---

    @staticmethod
    def handle_stripe_webhook(db: Session, event: dict) -> None:
        """Process a Stripe webhook event."""
        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Processing Stripe webhook: {event_type}")

        if event_type == "checkout.session.completed":
            BillingService._handle_checkout_completed(db, data)

        elif event_type == "customer.subscription.updated":
            BillingService._handle_subscription_updated(db, data)

        elif event_type == "customer.subscription.deleted":
            BillingService._handle_subscription_deleted(db, data)

        elif event_type == "invoice.paid":
            BillingService._handle_invoice_paid(db, data)

        elif event_type == "invoice.payment_failed":
            BillingService._handle_invoice_payment_failed(db, data)

    @staticmethod
    def _handle_checkout_completed(db: Session, session: dict) -> None:
        """Handle successful checkout."""
        org_id = int(session.get("metadata", {}).get("organization_id", 0))
        plan_name = session.get("metadata", {}).get("plan", "professional")
        subscription_id = session.get("subscription")

        if not org_id:
            logger.error("No organization_id in checkout session metadata")
            return

        sub = db.query(Subscription).filter(
            Subscription.organization_id == org_id
        ).first()

        if sub:
            sub.stripe_subscription_id = subscription_id
            sub.plan = SubscriptionPlan(plan_name)
            sub.status = SubscriptionStatus.ACTIVE

            # Update organization plan
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org:
                limits = PLAN_LIMITS[sub.plan]
                org.subscription_plan = plan_name
                org.max_users = limits["max_users"] if limits["max_users"] > 0 else 999
                org.subscription_status = "active"

            db.commit()

    @staticmethod
    def _handle_subscription_updated(db: Session, stripe_sub: dict) -> None:
        """Handle subscription update (plan change, renewal, etc.)."""
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub["id"]
        ).first()

        if not sub:
            return

        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "trialing": SubscriptionStatus.TRIALING,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELLED,
            "unpaid": SubscriptionStatus.UNPAID,
            "incomplete": SubscriptionStatus.INCOMPLETE,
        }

        sub.status = status_map.get(stripe_sub["status"], SubscriptionStatus.ACTIVE)
        sub.current_period_start = datetime.fromtimestamp(
            stripe_sub["current_period_start"], tz=timezone.utc
        )
        sub.current_period_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        )

        if stripe_sub.get("trial_end"):
            sub.trial_end = datetime.fromtimestamp(stripe_sub["trial_end"], tz=timezone.utc)

        db.commit()

    @staticmethod
    def _handle_subscription_deleted(db: Session, stripe_sub: dict) -> None:
        """Handle subscription cancellation."""
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub["id"]
        ).first()

        if not sub:
            return

        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = datetime.now(timezone.utc)
        sub.plan = SubscriptionPlan.STARTER  # Downgrade to free

        # Update organization
        org = db.query(Organization).filter(Organization.id == sub.organization_id).first()
        if org:
            org.subscription_plan = "starter"
            org.max_users = 1

        db.commit()

    @staticmethod
    def _handle_invoice_paid(db: Session, stripe_invoice: dict) -> None:
        """Handle successful invoice payment."""
        sub = db.query(Subscription).filter(
            Subscription.stripe_customer_id == stripe_invoice.get("customer")
        ).first()

        if not sub:
            return

        # Check if invoice already exists (idempotency protection)
        existing_invoice = db.query(Invoice).filter(
            Invoice.stripe_invoice_id == stripe_invoice["id"]
        ).first()

        if existing_invoice:
            logger.info(f"Invoice {stripe_invoice['id']} already processed, skipping")
            return

        invoice = Invoice(
            subscription_id=sub.id,
            organization_id=sub.organization_id,
            stripe_invoice_id=stripe_invoice["id"],
            status=InvoiceStatus.PAID,
            currency=stripe_invoice.get("currency", "gbp").upper(),
            amount_due=stripe_invoice.get("amount_due", 0),
            amount_paid=stripe_invoice.get("amount_paid", 0),
            amount_remaining=stripe_invoice.get("amount_remaining", 0),
            period_start=datetime.fromtimestamp(
                stripe_invoice["period_start"], tz=timezone.utc
            ) if stripe_invoice.get("period_start") else None,
            period_end=datetime.fromtimestamp(
                stripe_invoice["period_end"], tz=timezone.utc
            ) if stripe_invoice.get("period_end") else None,
            paid_at=datetime.now(timezone.utc),
            hosted_invoice_url=stripe_invoice.get("hosted_invoice_url"),
            invoice_pdf_url=stripe_invoice.get("invoice_pdf"),
        )
        db.add(invoice)
        db.commit()

    @staticmethod
    def _handle_invoice_payment_failed(db: Session, stripe_invoice: dict) -> None:
        """Handle failed invoice payment."""
        sub = db.query(Subscription).filter(
            Subscription.stripe_customer_id == stripe_invoice.get("customer")
        ).first()

        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            db.commit()

        logger.warning(
            f"Payment failed for customer {stripe_invoice.get('customer')}, "
            f"invoice {stripe_invoice.get('id')}"
        )
