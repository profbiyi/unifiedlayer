"""add billing tables (subscriptions, invoices, usage_records)

Revision ID: add_billing_001
Revises: add_api_keys_001
Create Date: 2026-01-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_billing_001'
down_revision: Union[str, None] = 'add_api_keys_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create billing tables."""
    # --- subscriptions ---
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('plan', sa.Enum('starter', 'professional', 'enterprise', name='subscriptionplan'), nullable=False, server_default='starter'),
        sa.Column('status', sa.Enum('active', 'trialing', 'past_due', 'cancelled', 'unpaid', 'incomplete', name='subscriptionstatus'), nullable=False, server_default='active'),
        sa.Column('payment_provider', sa.Enum('stripe', 'paystack', name='paymentprovider'), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('paystack_customer_code', sa.String(255), nullable=True),
        sa.Column('paystack_subscription_code', sa.String(255), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='GBP'),
        sa.Column('billing_email', sa.String(255), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('trial_end', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
        sa.UniqueConstraint('organization_id'),
        sa.UniqueConstraint('stripe_customer_id'),
        sa.UniqueConstraint('stripe_subscription_id'),
        sa.UniqueConstraint('paystack_customer_code'),
        sa.UniqueConstraint('paystack_subscription_code'),
    )
    op.create_index('ix_subscriptions_id', 'subscriptions', ['id'])
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'])
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])

    # --- invoices ---
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True),
        sa.Column('paystack_reference', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('draft', 'open', 'paid', 'void', 'uncollectible', name='invoicestatus'), nullable=False, server_default='draft'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='GBP'),
        sa.Column('amount_due', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('amount_paid', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('amount_remaining', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('hosted_invoice_url', sa.Text(), nullable=True),
        sa.Column('invoice_pdf_url', sa.Text(), nullable=True),
        sa.Column('line_items', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
        sa.UniqueConstraint('stripe_invoice_id'),
        sa.UniqueConstraint('paystack_reference'),
    )
    op.create_index('ix_invoices_id', 'invoices', ['id'])

    # --- usage_records ---
    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('period_year', sa.Integer(), nullable=False),
        sa.Column('period_month', sa.Integer(), nullable=False),
        sa.Column('rows_synced', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('api_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pipeline_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('active_connectors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_limit', sa.BigInteger(), nullable=False, server_default='10000'),
        sa.Column('api_calls_limit', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('rows_overage', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('overage_charged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'period_year', 'period_month', name='uq_usage_org_period'),
    )
    op.create_index('ix_usage_records_id', 'usage_records', ['id'])
    op.create_index('ix_usage_period', 'usage_records', ['period_year', 'period_month'])


def downgrade() -> None:
    """Drop billing tables."""
    op.drop_index('ix_usage_period', table_name='usage_records')
    op.drop_index('ix_usage_records_id', table_name='usage_records')
    op.drop_table('usage_records')

    op.drop_index('ix_invoices_id', table_name='invoices')
    op.drop_table('invoices')

    op.drop_index('ix_subscriptions_stripe_subscription_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_stripe_customer_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_id', table_name='subscriptions')
    op.drop_table('subscriptions')

    # Drop enums
    sa.Enum(name='invoicestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='paymentprovider').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='subscriptionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='subscriptionplan').drop(op.get_bind(), checkfirst=True)
