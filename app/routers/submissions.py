import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Submission, PendingBonus, Card, Player
from ..handoff import send_to_doskaz
from ..timeutil import utcnow_naive
from ..config import settings
from ..progression import active_multiplier, card_xp

router = APIRouter(prefix="/submissions", tags=["submissions"])
STORAGE_DIR = Path("storage/photos")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("")
async def create_submission(
    player_id: str = Form(...),
    card_id: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    card = await db.get(Card, card_id)
    if card is None or card.status != "claimed" or str(card.claimed_by_player_id) != player_id:
        raise HTTPException(status_code=400, detail="Card must be claimed by this player first")

    filename = f"{uuid.uuid4()}.jpg"
    filepath = STORAGE_DIR / filename
    with filepath.open("wb") as f:
        shutil.copyfileobj(photo.file, f)

    submission = Submission(
        player_id=player_id, card_id=card_id, lat=lat, lng=lng, photo_path=str(filepath),
        created_at=utcnow_naive(),
    )
    card.status = "submitted"
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    player = await db.get(Player, player_id)
    player.currency_balance += card.base_reward
    # XP is credited at the same moment as the coins; an active booster multiplies it.
    xp_gained = card_xp(card) * active_multiplier(player, utcnow_naive())
    player.xp += xp_gained
    submission.xp_awarded = xp_gained
    await db.commit()

    # --- Phase 6: hand off to doskaz (only when the switch is on) ---
    if settings.doskaz_handoff_enabled:
        submission.handoff_status, _ = await send_to_doskaz(
            photo_paths=[str(filepath)],
            name=f"TEST Meme Hunter {submission.id}",
            description="Test submission from the Meme Hunter game backend",
            address="Алматы",
            point=[lat, lng],
            category_id=28,
        )
    else:
        submission.handoff_status = "held"  # kept for review, sent to doskaz later
    await db.commit()

    # Player-facing result: the game accepted the photo. Doskaz delivery is internal.
    return {"submission_id": submission.id, "status": "sent", "reward": card.base_reward, "xp": xp_gained}