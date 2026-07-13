"""
Billing API routes.

Handles subscription management, checkout, usage tracking, and Stripe webhooks.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import User, Organization
from backend.models.billing import (
    Subscription,
    Invoice,
    UsageRecord,
    SubscriptionPlan,
    PLAN_LIMITS,
    REGIONAL_PRICING,
)
from backend.services.billing_service import BillingService
from backend.schemas.billing import (
    SubscriptionResponse,
    CreateCheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    UsageResponse,
    UsageLimitCheck,
    PlanDetailsResponse,
    RegionalPrice,
    AllPlansResponse,
    InvoiceResponse,
    DetailedUsageResponse,
    MetricUsage,
    UsageHistoryResponse,
)
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans", response_model=AllPlansResponse)
async def list_plans():
    """List all available subscription plans with their features and limits.

    Professional carries purchasing-power prices per market — each price is
    set against local affordability, not an FX conversion (see REGIONAL_PRICING).
    """
    professional_prices = [
        RegionalPrice(
            currency=currency,
            country=pricing["country"],
            symbol=pricing["symbol"],
            provider=pricing["provider"],
            monthly=pricing["professional_monthly"],
        )
        for currency, pricing in REGIONAL_PRICING.items()
    ]

    plans = []
    for plan, limits in PLAN_LIMITS.items():
        plans.append(PlanDetailsResponse(
            plan=plan.value,
            max_connectors=limits["max_connectors"],
            max_rows_per_month=limits["max_rows_per_month"],
            max_pipelines=limits["max_pipelines"],
            max_users=limits["max_users"],
            quality_checks=limits["quality_checks"],
            lineage=limits["lineage"],
            analytics=limits["analytics"],
            price_gbp=limits["price_gbp"],
            prices=professional_prices if plan == SubscriptionPlan.PROFESSIONAL else [],
        ))
    return AllPlansResponse(plans=plans)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current organization's subscription details."""
    sub = BillingService.get_subscription(db, current_user.organization_id)
    if not sub:
        # Create a default starter subscription
        sub = Subscription(
            organization_id=current_user.organization_id,
            plan=SubscriptionPlan.STARTER,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session to subscribe or upgrade."""
    if not getattr(settings, 'STRIPE_SECRET_KEY', None):
        raise HTTPException(status_code=400, detail="Stripe is not configured. Contact your administrator.")

    try:
        plan = SubscriptionPlan(request.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {request.plan}")

    if plan == SubscriptionPlan.STARTER:
        raise HTTPException(status_code=400, detail="Cannot checkout for the free plan.")

    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()

    # Ensure Stripe customer exists
    sub = BillingService.get_subscription(db, org.id)
    if not sub or not sub.stripe_customer_id:
        BillingService.create_stripe_customer(db, org, current_user)

    frontend_url = settings.FRONTEND_URL
    success_url = request.success_url or f"{frontend_url}/settings/billing?success=true"
    cancel_url = request.cancel_url or f"{frontend_url}/settings/billing?cancelled=true"

    try:
        checkout_url = BillingService.create_checkout_session(
            db, org, plan, success_url, cancel_url
        )
    except Exception as e:
        logger.error(f"Checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session.")

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing billing."""
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    frontend_url = settings.FRONTEND_URL

    try:
        portal_url = BillingService.create_portal_session(
            db, org, return_url=f"{frontend_url}/settings/billing"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PortalResponse(portal_url=portal_url)


@router.get("/usage", response_model=DetailedUsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current month's usage for the organization with per-metric limits and percentages."""
    record = BillingService.get_or_create_usage_record(db, current_user.organization_id)
    sub = BillingService.get_subscription(db, current_user.organization_id)
    plan = sub.plan if sub else SubscriptionPlan.STARTER
    limits = PLAN_LIMITS[plan]

    def _calc_metric(current: int, limit: int) -> MetricUsage:
        if limit == -1:  # Unlimited
            return MetricUsage(current=current, limit=-1, percent_used=0.0)
        if limit == 0:
            return MetricUsage(current=current, limit=0, percent_used=100.0 if current > 0 else 0.0)
        return MetricUsage(current=current, limit=limit, percent_used=round((current / limit) * 100, 1))

    return DetailedUsageResponse(
        period_year=record.period_year,
        period_month=record.period_month,
        plan=plan.value,
        rows_synced=_calc_metric(record.rows_synced, limits["max_rows_per_month"]),
        api_calls=_calc_metric(record.api_calls, record.api_calls_limit),
        pipeline_runs=_calc_metric(record.pipeline_runs, limits["max_pipelines"]),
        active_connectors=_calc_metric(record.active_connectors, limits["max_connectors"]),
    )


@router.get("/usage/history", response_model=UsageHistoryResponse)
async def get_usage_history(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the last N months of usage records for the organization."""
    from datetime import datetime, timezone
    datetime.now(timezone.utc)

    # Cap months to a reasonable range
    months = min(max(months, 1), 24)

    records = db.query(UsageRecord).filter(
        UsageRecord.organization_id == current_user.organization_id,
    ).order_by(
        UsageRecord.period_year.desc(),
        UsageRecord.period_month.desc(),
    ).limit(months).all()

    sub = BillingService.get_subscription(db, current_user.organization_id)
    plan = sub.plan if sub else SubscriptionPlan.STARTER

    results = []
    for r in records:
        usage_percent = 0.0
        if r.rows_limit > 0:
            usage_percent = round((r.rows_synced / r.rows_limit) * 100, 1)
        results.append(UsageResponse(
            period_year=r.period_year,
            period_month=r.period_month,
            rows_synced=r.rows_synced,
            api_calls=r.api_calls,
            pipeline_runs=r.pipeline_runs,
            storage_bytes=r.storage_bytes,
            active_connectors=r.active_connectors,
            rows_limit=r.rows_limit,
            usage_percent=usage_percent,
            plan=plan.value,
        ))
    return UsageHistoryResponse(records=results)


@router.get("/usage/check/{metric}", response_model=UsageLimitCheck)
async def check_usage_limit(
    metric: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if organization is within usage limits for a given metric."""
    if metric not in ("rows_synced", "connectors", "pipelines"):
        raise HTTPException(status_code=400, detail="Invalid metric. Use: rows_synced, connectors, pipelines")

    result = BillingService.check_usage_limit(db, current_user.organization_id, metric)
    return UsageLimitCheck(**result)


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all invoices for the organization."""
    invoices = db.query(Invoice).filter(
        Invoice.organization_id == current_user.organization_id
    ).order_by(Invoice.created_at.desc()).all()
    return invoices


@router.post("/paystack/checkout")
async def create_paystack_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Paystack transaction for African currency checkout (NGN, KES, GHS)."""
    try:
        plan = SubscriptionPlan(request.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {request.plan}")

    if plan == SubscriptionPlan.STARTER:
        raise HTTPException(status_code=400, detail="Cannot checkout for the free plan.")

    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()

    # Ensure Paystack customer exists
    sub = BillingService.get_subscription(db, org.id)
    if not sub or not sub.paystack_customer_code:
        BillingService.create_paystack_customer(db, org, current_user)
        sub = BillingService.get_subscription(db, org.id)

    frontend_url = settings.FRONTEND_URL
    callback_url = request.success_url or f"{frontend_url}/settings/billing?success=true"
    currency = getattr(request, 'currency', None) or sub.currency or "NGN"

    try:
        result = BillingService.create_paystack_checkout(
            plan=plan,
            email=current_user.email,
            callback_url=callback_url,
            currency=currency,
            metadata={
                "organization_id": str(org.id),
                "plan": plan.value,
            },
        )
    except Exception as e:
        logger.error(f"Paystack checkout failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Paystack checkout.")

    return {
        "authorization_url": result["authorization_url"],
        "reference": result["reference"],
        "access_code": result["access_code"],
    }


@router.get("/paystack/verify/{reference}")
async def verify_paystack_transaction(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify a Paystack transaction by reference."""
    try:
        data = BillingService.verify_paystack_transaction(reference)
    except Exception as e:
        logger.error(f"Paystack verification failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify transaction.")

    return {
        "status": data.get("status"),
        "reference": data.get("reference"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "paid_at": data.get("paid_at"),
        "channel": data.get("channel"),
    }


@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Paystack webhook events with HMAC SHA-512 verification."""
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Paystack signature.")

    try:
        BillingService.handle_paystack_webhook(db, payload, signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok"}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    import stripe as stripe_lib

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured.")

    try:
        event = stripe_lib.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe_lib.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload.")

    BillingService.handle_stripe_webhook(db, event)

    return {"status": "ok"}
