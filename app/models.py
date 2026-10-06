import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String)
    currency_balance: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

'''This is deliberately missing a doskaz_user_id column from our earlier schema sketch. Since every submission goes out under the one shared doskaz account for now, there's no per-player doskaz identity yet to store — that column comes back if a real per-player linkage becomes possible later.'''

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

'''Two reward fields now, not one: base_reward is credited instantly on submission; bonus_reward is what gets recorded as a pending bonus and only lands in the player's balance once you accept the submission in phase 7. status gains a lifecycle beyond just active/inactive: active → claimed → submitted.'''