from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Card

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/nearby")
async def nearby_cards(lat: float, lng: float, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.status == "active"))
    return result.scalars().all()


@router.post("/{card_id}/claim")
async def claim_card(card_id: str, player_id: str = Form(...), db: AsyncSession = Depends(get_db)):
    card = await db.get(Card, card_id)
    if card is None or card.status != "active":
        raise HTTPException(status_code=400, detail="Card not available to claim")

    card.status = "claimed"
    card.claimed_by_player_id = player_id
    card.claimed_at = datetime.now(timezone.utc).replace(tzinfo=None)  # Store as naive UTC datetime
    await db.commit()

    return {"card_id": card.id, "lat": card.lat, "lng": card.lng, "rarity": card.rarity}

'''nearby_cards is unchanged from before: lat/lng are accepted but not used to filter yet — every active card comes back, proving the response shape before real distance filtering exists. 
claim_card is the new piece this revision calls for: this is the exact moment the backend hands over a card's real lat/lng to the client — not before, and this response is where that data exists. 
Claiming also locks the card (status="claimed", tagged with who and when) so a second player can't claim the same card, and — as phase 5 enforces — only the claiming player can submit against it.'''