"""005_stage5_purchases

Revision ID: 20261011_005
Revises: 20261011_004
Create Date: 2026-10-11 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261011_005'
down_revision: Union[str, None] = '20261011_004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Suppliers Table
    op.create_table(
        'suppliers',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('current_balance', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_suppliers_business_id', 'suppliers', ['business_id'])
    op.create_index('ix_suppliers_name', 'suppliers', ['name'])
    op.create_index('ix_suppliers_phone', 'suppliers', ['phone'])

    # 2. Supplier Ledger Entries Table
    op.create_table(
        'supplier_ledger_entries',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('supplier_id', sa.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entry_type', sa.String(50), nullable=False),
        sa.Column('reference_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('balance_after', sa.Numeric(14, 4), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_supplier_ledger_entries_business_id', 'supplier_ledger_entries', ['business_id'])
    op.create_index('ix_supplier_ledger_entries_supplier_id', 'supplier_ledger_entries', ['supplier_id'])
    op.create_index('ix_supplier_ledger_entries_reference_id', 'supplier_ledger_entries', ['reference_id'])
    op.create_index('ix_supplier_ledger_entries_created_at', 'supplier_ledger_entries', ['created_at'])

    # 3. Purchases Table
    op.create_table(
        'purchases',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', sa.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', sa.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('supplier_id', sa.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('supplier_invoice_ref', sa.String(100), nullable=True),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), server_default='received', nullable=False),
        sa.Column('subtotal_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('tax_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('total_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('paid_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('credit_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('payment_status', sa.String(30), nullable=False),
        sa.Column('purchase_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'invoice_number', name='uq_purchases_business_invoice_number'),
        sa.UniqueConstraint('business_id', 'idempotency_key', name='uq_purchases_business_idempotency_key'),
    )
    op.create_index('ix_purchases_business_id', 'purchases', ['business_id'])
    op.create_index('ix_purchases_supplier_id', 'purchases', ['supplier_id'])
    op.create_index('ix_purchases_invoice_number', 'purchases', ['invoice_number'])
    op.create_index('ix_purchases_idempotency_key', 'purchases', ['idempotency_key'])
    op.create_index('ix_purchases_purchase_date', 'purchases', ['purchase_date'])

    # 4. Purchase Items Table
    op.create_table(
        'purchase_items',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('purchase_id', sa.UUID(as_uuid=True), sa.ForeignKey('purchases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_amount', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('total_cost', sa.Numeric(14, 4), nullable=False),
        sa.Column('effective_unit_cost', sa.Numeric(14, 4), nullable=False),
    )
    op.create_index('ix_purchase_items_purchase_id', 'purchase_items', ['purchase_id'])
    op.create_index('ix_purchase_items_product_id', 'purchase_items', ['product_id'])

    # 5. Add purchase_id and supplier_id columns to Payments table
    op.add_column('payments', sa.Column('purchase_id', sa.UUID(as_uuid=True), sa.ForeignKey('purchases.id', ondelete='SET NULL'), nullable=True))
    op.add_column('payments', sa.Column('supplier_id', sa.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_payments_purchase_id', 'payments', ['purchase_id'])
    op.create_index('ix_payments_supplier_id', 'payments', ['supplier_id'])


def downgrade() -> None:
    op.drop_index('ix_payments_supplier_id', table_name='payments')
    op.drop_index('ix_payments_purchase_id', table_name='payments')
    op.drop_column('payments', 'supplier_id')
    op.drop_column('payments', 'purchase_id')
    op.drop_table('purchase_items')
    op.drop_table('purchases')
    op.drop_table('supplier_ledger_entries')
    op.drop_table('suppliers')
