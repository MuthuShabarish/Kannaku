"""003_stage3_inventory

Revision ID: 20261011_003
Revises: 20261010_002
Create Date: 2026-10-11 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261011_003'
down_revision: Union[str, None] = '20261010_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Categories Table
    op.create_table(
        'categories',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tamil_name', sa.String(255), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'name', name='uq_categories_business_name'),
    )
    op.create_index('ix_categories_business_id', 'categories', ['business_id'])

    # 2. Products Table
    op.create_table(
        'products',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tamil_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('unit', sa.String(50), server_default='piece', nullable=False),
        sa.Column('purchase_cost', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('selling_price', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('low_stock_threshold', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'sku', name='uq_products_business_sku'),
    )
    op.create_index('ix_products_business_id', 'products', ['business_id'])
    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_index('ix_products_sku', 'products', ['sku'])

    # 3. Inventory Balances Table
    op.create_table(
        'inventory_balances',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', sa.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('current_stock', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('reserved_stock', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('average_cost', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('warehouse_id', 'product_id', name='uq_inventory_balance_warehouse_product'),
        sa.CheckConstraint('current_stock >= 0', name='chk_current_stock_non_negative'),
    )
    op.create_index('ix_inventory_balances_business_id', 'inventory_balances', ['business_id'])
    op.create_index('ix_inventory_balances_warehouse_id', 'inventory_balances', ['warehouse_id'])
    op.create_index('ix_inventory_balances_product_id', 'inventory_balances', ['product_id'])

    # 4. Stock Movements Table
    op.create_table(
        'stock_movements',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', sa.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('movement_type', sa.String(50), nullable=False),
        sa.Column('quantity_delta', sa.Numeric(14, 4), nullable=False),
        sa.Column('balance_after', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_stock_movements_business_id', 'stock_movements', ['business_id'])
    op.create_index('ix_stock_movements_warehouse_id', 'stock_movements', ['warehouse_id'])
    op.create_index('ix_stock_movements_product_id', 'stock_movements', ['product_id'])
    op.create_index('ix_stock_movements_created_by_user_id', 'stock_movements', ['created_by_user_id'])
    op.create_index('ix_stock_movements_created_at', 'stock_movements', ['created_at'])


def downgrade() -> None:
    op.drop_table('stock_movements')
    op.drop_table('inventory_balances')
    op.drop_table('products')
    op.drop_table('categories')
