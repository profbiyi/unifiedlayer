"""
Billing Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class SubscriptionResponse(BaseModel):
    public_id: UUID
    plan: str
    status: str
    payment_provider: Optional[str] = None
    currency: str = "GBP"
    billing_email: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateCheckoutRequest(BaseModel):
    plan: str = Field(..., description="Plan to subscribe to: professional or enterprise")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class MetricUsage(BaseModel):
    current: int = 0
    limit: int = -1  # -1 means unlimited
    percent_used: float = 0.0


class UsageResponse(BaseModel):
    period_year: int
    period_month: int
    rows_synced: int = 0
    api_calls: int = 0
    pipeline_runs: int = 0
    storage_bytes: int = 0
    active_connectors: int = 0
    rows_limit: int = 10_000
    usage_percent: float = 0.0
    plan: str = "starter"

    class Config:
        from_attributes = True


class DetailedUsageResponse(BaseModel):
    period_year: int
    period_month: int
    plan: str = "starter"
    rows_synced: MetricUsage
    api_calls: MetricUsage
    pipeline_runs: MetricUsage
    active_connectors: MetricUsage

    class Config:
        from_attributes = True


class UsageHistoryResponse(BaseModel):
    records: List[UsageResponse]


class UsageLimitCheck(BaseModel):
    allowed: bool
    current: int
    limit: int
    usage_percent: float = 0.0
    plan: str = "starter"


class PlanDetailsResponse(BaseModel):
    plan: str
    max_connectors: int
    max_rows_per_month: int
    max_pipelines: int
    max_users: int
    quality_checks: bool
    lineage: bool
    analytics: bool
    price_gbp: Optional[int] = None


class AllPlansResponse(BaseModel):
    plans: List[PlanDetailsResponse]


class InvoiceResponse(BaseModel):
    public_id: UUID
    status: str
    currency: str
    amount_due: int
    amount_paid: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    hosted_invoice_url: Optional[str] = None
    invoice_pdf_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
