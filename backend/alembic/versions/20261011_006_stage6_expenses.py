"""006_stage6_expenses

Revision ID: 20261011_006
Revises: 20261011_005
Create Date: 2026-10-11 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261011_006'
down_revision: Union[str, None] = '20261011_005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Expense Categories Table
    op.create_table(
        'expense_categories',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'name', name='uq_expense_category_business_name'),
    )
    op.create_index('ix_expense_categories_business_id', 'expense_categories', ['business_id'])
    op.create_index('ix_expense_categories_name', 'expense_categories', ['name'])

    # 2. Expenses Table
    op.create_table(
        'expenses',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.UUID(as_uuid=True), sa.ForeignKey('expense_categories.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('expense_number', sa.String(100), nullable=False),
        sa.Column('amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('expense_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('payment_method', sa.String(30), server_default='cash', nullable=False),
        sa.Column('payment_status', sa.String(20), server_default='paid', nullable=False),
        sa.Column('payee', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'expense_number', name='uq_expense_business_number'),
        sa.UniqueConstraint('business_id', 'idempotency_key', name='uq_expense_business_idempotency'),
    )
    op.create_index('ix_expenses_business_id', 'expenses', ['business_id'])
    op.create_index('ix_expenses_category_id', 'expenses', ['category_id'])
    op.create_index('ix_expenses_expense_number', 'expenses', ['expense_number'])
    op.create_index('ix_expenses_expense_date', 'expenses', ['expense_date'])
    op.create_index('ix_expenses_payment_status', 'expenses', ['payment_status'])
    op.create_index('ix_expenses_idempotency_key', 'expenses', ['idempotency_key'])


def downgrade() -> None:
    op.drop_index('ix_expenses_idempotency_key', table_name='expenses')
    op.drop_index('ix_expenses_payment_status', table_name='expenses')
    op.drop_index('ix_expenses_expense_date', table_name='expenses')
    op.drop_index('ix_expenses_expense_number', table_name='expenses')
    op.drop_index('ix_expenses_category_id', table_name='expenses')
    op.drop_index('ix_expenses_business_id', table_name='expenses')
    op.drop_table('expenses')
    op.drop_index('ix_expense_categories_name', table_name='expense_categories')
    op.drop_index('ix_expense_categories_business_id', table_name='expense_categories')
    op.drop_table('expense_categories')
