import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, func
from sqlalchemy import Float, ForeignKey, Computed
from geoalchemy2 import Geometry
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID, JSONB


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String)
    currency_balance: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)  # unused; progression uses xp + rank
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Progression (see app/progression.py): xp only grows; rank is derived from it, never stored.
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    xp_booster_multiplier: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 2 or 5
    xp_booster_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # naive UTC

'''This is deliberately missing a doskaz_user_id column from our earlier schema sketch. 
Since every submission goes out under the one shared doskaz account for now, there's no per-player 
doskaz identity yet to store — that column comes back if a real per-player linkage becomes possible later.'''

class Card(Base):
    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    rarity: Mapped[str] = mapped_column(String, default="common")
    base_reward: Mapped[int] = mapped_column(Integer, default=10)
    bonus_reward: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String, default="active")
    claimed_by_player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # PostGIS point computed by the database from lat/lng, so it can never disagree with them.
    # Cards inserted by hand with only lat/lng still get it. Used for zone checks (and later radius search).
    location = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False),
        Computed("ST_SetSRID(ST_MakePoint(lng, lat), 4326)", persisted=True),
    )

'''Two reward fields now, not one: base_reward is credited instantly on submission; 
bonus_reward is what gets recorded as a pending bonus and only lands in the player's 
balance once you accept the submission in phase 7. status gains a lifecycle beyond just 
active/inactive: active → claimed → submitted.'''

class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    card_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cards.id"))
    handoff_status: Mapped[str] = mapped_column(String, default="pending")
    review_status: Mapped[str] = mapped_column(String, default="pending")
    photo_path: Mapped[str] = mapped_column(String, nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Staff review (set on the review page)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    accessibility: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # incl. booster


class PendingBonus(Base):
    __tablename__ = "pending_bonuses"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submissions.id"), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    credited_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

'''Two fields replace the old single status on Submission: handoff_status tracks whether this backend successfully got the data to doskaz 
(that's a pipeline/plumbing concern); review_status tracks doskaz's actual accept/reject decision (a content concern, set later in phase 7). 
Keeping them separate avoids the confusing overload where "approved" used to mean two different things. PendingBonus is its own table, one row 
per submission (unique=True on submission_id), exactly as specified: the deferred bonus lives at the submission level, not folded into 
the player row, because a submission's bonus can be voided independently of anything else about the player.'''

class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="reviewer")  # "admin" or "reviewer"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

'''Staff are the people who run the game (admins and reviewers). They are kept apart from players on purpose,
so a player account can never gain review rights. Only a bcrypt hash of the password is stored.'''



class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # "restricted" or "dangerous": both mean no cards here
    area = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=False))  # Polygon or MultiPolygon
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

'''Zones are areas where no card may exist: restricted (not allowed in) or dangerous (roads, rail, water, construction).
For spawning both kinds behave the same; the kind is kept so the admin and the thesis can tell why a zone exists.
Spatial indexes are created in the migration by name (spatial_index=False here), so Alembic does not try to manage them twice.'''
