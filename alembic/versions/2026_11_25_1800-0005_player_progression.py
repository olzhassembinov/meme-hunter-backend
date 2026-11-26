"""player progression: xp, xp booster, xp awarded per submission

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-25 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('players', sa.Column('xp', sa.Integer(), server_default='0', nullable=False))
    op.add_column('players', sa.Column('xp_booster_multiplier', sa.Integer(), nullable=True))
    op.add_column('players', sa.Column('xp_booster_expires_at', sa.DateTime(), nullable=True))
    op.add_column('submissions', sa.Column('xp_awarded', sa.Integer(), server_default='0', nullable=False))

    # Give existing players the XP of their past catches (rejected ones excluded): card coins x 5.
    op.execute("""
        UPDATE submissions s SET xp_awarded = c.base_reward * 5
        FROM cards c
        WHERE c.id = s.card_id AND s.review_status <> 'rejected'
    """)
    op.execute("""
        UPDATE players p SET xp = t.total
        FROM (SELECT player_id, SUM(xp_awarded) AS total FROM submissions GROUP BY player_id) t
        WHERE t.player_id = p.id
    """)


def downgrade() -> None:
    op.drop_column('submissions', 'xp_awarded')
    op.drop_column('players', 'xp_booster_expires_at')
    op.drop_column('players', 'xp_booster_multiplier')
    op.drop_column('players', 'xp')
