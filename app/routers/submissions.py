import shutil
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Submission, PendingBonus, Card, Player
from ..doskaz_client import DoskazClient

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
    )
    card.status = "submitted"
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    player = await db.get(Player, player_id)
    player.currency_balance += card.base_reward
    await db.commit()

    # --- Phase 6: hand off to doskaz ---
    doskaz = DoskazClient()
    try:
        photo_url = await doskaz.upload_photo(str(filepath))
        await doskaz.submit_facility(
            name=f"TEST Meme Hunter {submission.id}",
            description="Test submission from the Meme Hunter game backend",
            address="Алматы",
            point=[lat, lng],
            category_id=28,
            photo_paths=[photo_url],
        )
        submission.handoff_status = "sent"
    except httpx.HTTPStatusError as e:
        print("doskaz rejected the request:", e.request.url, e.response.status_code, e.response.text)
        submission.handoff_status = "failed"
    except httpx.HTTPError as e:
        print("could not reach doskaz:", repr(e))
        submission.handoff_status = "failed"
    await db.commit()

    return {"submission_id": submission.id, "status": submission.handoff_status, "reward": card.base_reward}