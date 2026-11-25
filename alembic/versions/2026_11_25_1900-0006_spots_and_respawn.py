"""spots, card respawn and claim timeout

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-25 19:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('spots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('location', Geometry('POINT', srid=4326, spatial_index=False),
                  sa.Computed('ST_SetSRID(ST_MakePoint(lng, lat), 4326)', persisted=True)),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_spots_location_gist', 'spots', ['location'], postgresql_using='gist')
    op.add_column('cards', sa.Column('spot_id', sa.UUID(), nullable=True))
    op.add_column('cards', sa.Column('respawn_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('cards_spot_id_fkey', 'cards', 'spots', ['spot_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('cards_spot_id_fkey', 'cards', type_='foreignkey')
    op.drop_column('cards', 'respawn_at')
    op.drop_column('cards', 'spot_id')
    op.drop_index('idx_spots_location_gist', table_name='spots')
    op.drop_table('spots')
