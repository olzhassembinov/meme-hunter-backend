"""Claim timeout and card respawn (a light version of the priority algorithm).

All tunable numbers live here. A background loop (started in main.py) runs both jobs every minute.
"""
import asyncio
import logging
import random
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session
from .models import Card, Spot, Submission
from .timeutil import utcnow_naive
from .zones import not_allowed, point

log = logging.getLogger("spawning")

CLAIM_TIMEOUT = timedelta(minutes=30)  # a claimed card is released if no photo comes in time
RESPAWN_DELAY = timedelta(hours=1)     # a caught card's slot gets a new card after this
TARGET_PHOTOS = 10                      # a spot with this many photos counts as well covered
JOB_INTERVAL_SECONDS = 60

COINS = {"common": 10, "rare": 20, "epic": 40, "legendary": 80}
# Rarity chances for a spot with no photos (need = 1) and a well covered one (need = 0); linear in between.
CHANCES_NEED_1 = {"legendary": 0.15, "epic": 0.25, "rare": 0.35, "common": 0.25}
CHANCES_NEED_0 = {"legendary": 0.05, "epic": 0.10, "rare": 0.25, "common": 0.60}


def rarity_chances(need: float) -> dict[str, float]:
    return {r: CHANCES_NEED_0[r] + (CHANCES_NEED_1[r] - CHANCES_NEED_0[r]) * need for r in COINS}


def pick_rarity(need: float, rng: random.Random = random) -> str:
    chances = rarity_chances(need)
    roll, total = rng.random(), 0.0
    for rarity in ("legendary", "epic", "rare", "common"):
        total += chances[rarity]
        if roll < total:
            return rarity
    return "common"


async def spot_photo_count(db: AsyncSession, spot_id) -> int:
    """Photos taken at a spot that were not rejected (pending ones count: review may lag behind)."""
    return (await db.execute(
        select(func.count()).select_from(Submission)
        .join(Card, Card.id == Submission.card_id)
        .where(Card.spot_id == spot_id, Submission.review_status != "rejected")
    )).scalar_one()


def spot_need(photos: int) -> float:
    return max(0.0, 1.0 - photos / TARGET_PHOTOS)


async def release_expired_claims(db: AsyncSession) -> int:
    result = await db.execute(
        update(Card)
        .where(Card.status == "claimed", Card.claimed_at < utcnow_naive() - CLAIM_TIMEOUT)
        .values(status="active", claimed_by_player_id=None, claimed_at=None)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


async def respawn_cards(db: AsyncSession) -> int:
    now = utcnow_naive()
    due = (await db.execute(
        select(Card).join(Spot, Spot.id == Card.spot_id)
        .where(Card.status == "submitted", Card.respawn_at <= now, Spot.is_active.is_(True))
    )).scalars().all()
    created = 0
    for old in due:
        old.respawn_at = None  # this slot is handled; the new card carries it on
        if (await db.execute(select(not_allowed(point(old.lat, old.lng))))).scalar():
            continue  # the place is now in a blocked zone or outside the play area: the slot ends here
        need = spot_need(await spot_photo_count(db, old.spot_id))
        rarity = pick_rarity(need)
        db.add(Card(lat=old.lat, lng=old.lng, spot_id=old.spot_id, rarity=rarity,
                    base_reward=COINS[rarity], status="active"))
        created += 1
    return created


async def run_jobs_once() -> tuple[int, int]:
    async with async_session() as db:
        released = await release_expired_claims(db)
        respawned = await respawn_cards(db)
        await db.commit()
    return released, respawned


async def jobs_loop() -> None:
    while True:
        try:
            released, respawned = await run_jobs_once()
            if released or respawned:
                log.warning("spawning: released %d claims, respawned %d cards", released, respawned)
        except Exception:  # keep the loop alive; the next run retries
            log.exception("spawning job failed")
        await asyncio.sleep(JOB_INTERVAL_SECONDS)
