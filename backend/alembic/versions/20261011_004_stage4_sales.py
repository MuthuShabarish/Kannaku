"""004_stage4_sales

Revision ID: 20261011_004
Revises: 20261011_003
Create Date: 2026-10-11 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261011_004'
down_revision: Union[str, None] = '20261011_003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Customers Table
    op.create_table(
        'customers',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('credit_limit', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('current_balance', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'phone', name='uq_customers_business_phone'),
    )
    op.create_index('ix_customers_business_id', 'customers', ['business_id'])
    op.create_index('ix_customers_phone', 'customers', ['phone'])
    op.create_index('ix_customers_name', 'customers', ['name'])

    # 2. Customer Ledger Entries Table
    op.create_table(
        'customer_ledger_entries',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entry_type', sa.String(50), nullable=False),
        sa.Column('reference_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('balance_after', sa.Numeric(14, 4), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_customer_ledger_entries_business_id', 'customer_ledger_entries', ['business_id'])
    op.create_index('ix_customer_ledger_entries_customer_id', 'customer_ledger_entries', ['customer_id'])
    op.create_index('ix_customer_ledger_entries_reference_id', 'customer_ledger_entries', ['reference_id'])
    op.create_index('ix_customer_ledger_entries_created_at', 'customer_ledger_entries', ['created_at'])

    # 3. Sales Table
    op.create_table(
        'sales',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', sa.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', sa.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), server_default='completed', nullable=False),
        sa.Column('subtotal_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('tax_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('total_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('paid_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('credit_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('cogs_total', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('payment_status', sa.String(30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'invoice_number', name='uq_sales_business_invoice_number'),
        sa.UniqueConstraint('business_id', 'idempotency_key', name='uq_sales_business_idempotency_key'),
    )
    op.create_index('ix_sales_business_id', 'sales', ['business_id'])
    op.create_index('ix_sales_customer_id', 'sales', ['customer_id'])
    op.create_index('ix_sales_invoice_number', 'sales', ['invoice_number'])
    op.create_index('ix_sales_idempotency_key', 'sales', ['idempotency_key'])
    op.create_index('ix_sales_created_at', 'sales', ['created_at'])

    # 4. Sale Items Table
    op.create_table(
        'sale_items',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('sale_id', sa.UUID(as_uuid=True), sa.ForeignKey('sales.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('total_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(14, 4), nullable=False),
        sa.Column('line_cogs', sa.Numeric(14, 4), nullable=False),
    )
    op.create_index('ix_sale_items_sale_id', 'sale_items', ['sale_id'])
    op.create_index('ix_sale_items_product_id', 'sale_items', ['product_id'])

    # 5. Payments Table
    op.create_table(
        'payments',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sale_id', sa.UUID(as_uuid=True), sa.ForeignKey('sales.id', ondelete='SET NULL'), nullable=True),
        sa.Column('customer_id', sa.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payment_direction', sa.String(20), server_default='inflow', nullable=False),
        sa.Column('payment_mode', sa.String(30), nullable=False),
        sa.Column('amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_payments_business_id', 'payments', ['business_id'])
    op.create_index('ix_payments_sale_id', 'payments', ['sale_id'])
    op.create_index('ix_payments_customer_id', 'payments', ['customer_id'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])


def downgrade() -> None:
    op.drop_table('payments')
    op.drop_table('sale_items')
    op.drop_table('sales')
    op.drop_table('customer_ledger_entries')
    op.drop_table('customers')
