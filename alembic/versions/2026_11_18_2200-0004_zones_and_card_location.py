"""zones and card location (PostGIS)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry


revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS: already present on the server's postgis/postgis image; enabled here for local databases.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # cards.location is computed by Postgres from lng/lat, so existing and hand-inserted cards get it too.
    op.add_column('cards', sa.Column(
        'location', Geometry('POINT', srid=4326, spatial_index=False),
        sa.Computed('ST_SetSRID(ST_MakePoint(lng, lat), 4326)', persisted=True),
    ))
    op.create_index('idx_cards_location_gist', 'cards', ['location'], postgresql_using='gist')

    op.create_table('zones',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('area', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_zones_area_gist', 'zones', ['area'], postgresql_using='gist')


def downgrade() -> None:
    op.drop_index('idx_zones_area_gist', table_name='zones')
    op.drop_table('zones')
    op.drop_index('idx_cards_location_gist', table_name='cards')
    op.drop_column('cards', 'location')
    # The postgis extension is left installed: other things may use it.
