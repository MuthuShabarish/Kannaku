"""002_stage2_onboarding

Revision ID: 20261010_002
Revises: 20261010_001
Create Date: 2026-10-10 20:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261010_002'
down_revision: Union[str, None] = '20261010_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend businesses table with Stage 2 adaptive onboarding columns
    op.add_column('businesses', sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('businesses', sa.Column('onboarding_step', sa.Integer(), server_default='1', nullable=False))
    op.add_column('businesses', sa.Column('onboarding_answers', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('businesses', sa.Column('recommended_tier', sa.String(20), nullable=True))
    op.add_column('businesses', sa.Column('recommendation_reasons', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('businesses', sa.Column('enabled_modules', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('businesses', sa.Column('workforce_count', sa.Integer(), server_default='1', nullable=False))
    op.add_column('businesses', sa.Column('app_users_count', sa.Integer(), server_default='1', nullable=False))
    op.add_column('businesses', sa.Column('branch_count', sa.Integer(), server_default='1', nullable=False))
    op.add_column('businesses', sa.Column('warehouse_count', sa.Integer(), server_default='1', nullable=False))
    op.add_column('businesses', sa.Column('operations', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('businesses', sa.Column('accessibility_settings', sa.JSON(), server_default='{}', nullable=False))


def downgrade() -> None:
    op.drop_column('businesses', 'accessibility_settings')
    op.drop_column('businesses', 'operations')
    op.drop_column('businesses', 'warehouse_count')
    op.drop_column('businesses', 'branch_count')
    op.drop_column('businesses', 'app_users_count')
    op.drop_column('businesses', 'workforce_count')
    op.drop_column('businesses', 'enabled_modules')
    op.drop_column('businesses', 'recommendation_reasons')
    op.drop_column('businesses', 'recommended_tier')
    op.drop_column('businesses', 'onboarding_answers')
    op.drop_column('businesses', 'onboarding_step')
    op.drop_column('businesses', 'onboarding_completed')
