import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Card, Player, Submission
from ..progression import BOOSTER_DURATION, BOOSTER_PRICES, profile
from ..schemas import PlayerCreate
from ..streak import FREEZE_MAX, FREEZE_PRICE
from ..timeutil import utcnow_naive

router = APIRouter(prefix="/players", tags=["players"])


class BoosterBuy(BaseModel):
    multiplier: Literal[2, 5]


@router.post("")
async def create_player(data: PlayerCreate, db: AsyncSession = Depends(get_db)):
    player = Player(display_name=data.display_name, xp=0)
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return profile(player, utcnow_naive())


@router.get("/{player_id}")
async def get_player(player_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return profile(player, utcnow_naive())


@router.post("/{player_id}/boosters/xp")
async def buy_xp_booster(player_id: uuid.UUID, data: BoosterBuy, db: AsyncSession = Depends(get_db)):
    # Row lock: two quick taps cannot both pass the balance check.
    player = (await db.execute(select(Player).where(Player.id == player_id).with_for_update())).scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    price = BOOSTER_PRICES[data.multiplier]
    if player.currency_balance < price:
        raise HTTPException(status_code=400, detail="Not enough coins")
    now = utcnow_naive()
    player.currency_balance -= price
    player.xp_booster_multiplier = data.multiplier  # a new booster replaces an active one, no stacking
    player.xp_booster_expires_at = now + BOOSTER_DURATION
    await db.commit()
    await db.refresh(player)
    return profile(player, now)


@router.post("/{player_id}/streak-freeze/buy")
async def buy_streak_freeze(player_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    player = (await db.execute(select(Player).where(Player.id == player_id).with_for_update())).scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    if player.streak_freeze_count >= FREEZE_MAX:
        raise HTTPException(status_code=400, detail="Freeze limit reached")
    if player.currency_balance < FREEZE_PRICE:
        raise HTTPException(status_code=400, detail="Not enough coins")
    player.currency_balance -= FREEZE_PRICE
    player.streak_freeze_count += 1
    await db.commit()
    await db.refresh(player)
    return profile(player, utcnow_naive())


@router.get("/{player_id}/collection")
async def get_collection(player_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if await db.get(Player, player_id) is None:
        raise HTTPException(status_code=404, detail="Player not found")
    rows = (await db.execute(
        select(Submission, Card)
        .join(Card, Card.id == Submission.card_id)
        .where(Submission.player_id == player_id, Submission.review_status != "rejected")
        .order_by(Submission.created_at.desc())
    )).all()
    by_rarity = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
    cards = []
    for sub, card in rows:
        by_rarity[card.rarity] = by_rarity.get(card.rarity, 0) + 1
        cards.append({
            "card_id": card.id,
            "rarity": card.rarity,
            "collected_at": sub.created_at.isoformat() + "Z",
            "coins": card.base_reward,
            "xp": sub.xp_awarded,
        })
    return {"total": len(cards), "by_rarity": by_rarity, "cards": cards}

'''Player-facing profile, booster and collection endpoints. Rejected submissions are left out of the collection
(their coins and XP stay credited, like the instant reward). Timestamps are UTC with a trailing "Z".'''
