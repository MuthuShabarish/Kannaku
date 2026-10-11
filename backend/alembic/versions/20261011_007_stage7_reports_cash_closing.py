"""007_stage7_reports_cash_closing

Revision ID: 20261011_007
Revises: 20261011_006
Create Date: 2026-10-11 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261011_007'
down_revision: Union[str, None] = '20261011_006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Daily Cash Closings Table
    op.create_table(
        'daily_cash_closings',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', sa.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', sa.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=True),
        sa.Column('closing_date', sa.Date(), nullable=False),
        sa.Column('session_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('opening_cash', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('cash_inflows', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('cash_outflows', sa.Numeric(14, 4), server_default='0.0000', nullable=False),
        sa.Column('expected_cash', sa.Numeric(14, 4), nullable=False),
        sa.Column('actual_cash', sa.Numeric(14, 4), nullable=False),
        sa.Column('difference', sa.Numeric(14, 4), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), server_default='closed', nullable=False),
        sa.Column('closed_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reopened_by_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reopen_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('business_id', 'closing_date', name='uq_cash_closing_business_date'),
    )
    op.create_index('ix_daily_cash_closings_business_id', 'daily_cash_closings', ['business_id'])
    op.create_index('ix_daily_cash_closings_branch_id', 'daily_cash_closings', ['branch_id'])
    op.create_index('ix_daily_cash_closings_closing_date', 'daily_cash_closings', ['closing_date'])
    op.create_index('ix_daily_cash_closings_status', 'daily_cash_closings', ['status'])
    op.create_index('ix_daily_cash_closings_closed_by_user_id', 'daily_cash_closings', ['closed_by_user_id'])


def downgrade() -> None:
    op.drop_index('ix_daily_cash_closings_closed_by_user_id', table_name='daily_cash_closings')
    op.drop_index('ix_daily_cash_closings_status', table_name='daily_cash_closings')
    op.drop_index('ix_daily_cash_closings_closing_date', table_name='daily_cash_closings')
    op.drop_index('ix_daily_cash_closings_branch_id', table_name='daily_cash_closings')
    op.drop_index('ix_daily_cash_closings_business_id', table_name='daily_cash_closings')
    op.drop_table('daily_cash_closings')
