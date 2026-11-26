"""daily streak: current streak, last active day, streak freezes

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-26 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing players start with no streak; it begins with their next photo submission.
    op.add_column('players', sa.Column('current_streak', sa.Integer(), server_default='0', nullable=False))
    op.add_column('players', sa.Column('last_active_date', sa.Date(), nullable=True))
    op.add_column('players', sa.Column('streak_freeze_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('players', 'streak_freeze_count')
    op.drop_column('players', 'last_active_date')
    op.drop_column('players', 'current_streak')
