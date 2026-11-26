import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..admin_auth import require_admin
from ..database import get_db
from ..models import Card, Spot, Submission
from ..spawning import spot_need
from ..zones import not_allowed, point

router = APIRouter(prefix="/admin", tags=["admin: spots"], dependencies=[Depends(require_admin)])

LINK_RADIUS_M = 15  # existing cards this close to a new spot become its slots


class SpotCreate(BaseModel):
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


@router.post("/spots")
async def create_spot(data: SpotCreate, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(not_allowed(point(data.lat, data.lng))))).scalar():
        raise HTTPException(status_code=409, detail="Point is inside a blocked zone or outside the play area")
    spot = Spot(id=uuid.uuid4(), name=data.name, lat=data.lat, lng=data.lng, is_active=True)
    db.add(spot)
    await db.flush()
    linked = await db.execute(
        update(Card)
        .where(Card.spot_id.is_(None),
               func.ST_DWithin(func.Geography(Card.location), func.Geography(point(data.lat, data.lng)), LINK_RADIUS_M))
        .values(spot_id=spot.id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return {"id": spot.id, "name": spot.name, "lat": spot.lat, "lng": spot.lng, "cards_linked": linked.rowcount}


@router.get("/spots")
async def list_spots(db: AsyncSession = Depends(get_db)):
    photos = (
        select(Card.spot_id, func.count().label("photos"))
        .join(Submission, Submission.card_id == Card.id)
        .where(Submission.review_status != "rejected")
        .group_by(Card.spot_id).subquery()
    )
    cards = (
        select(Card.spot_id,
               func.count().filter(Card.status == "active").label("active"),
               func.count().filter(Card.status == "claimed").label("claimed"),
               func.count().filter(and_(Card.status == "submitted", Card.respawn_at.is_not(None))).label("respawning"))
        .group_by(Card.spot_id).subquery()
    )
    rows = (await db.execute(
        select(Spot, func.coalesce(photos.c.photos, 0), func.coalesce(cards.c.active, 0),
               func.coalesce(cards.c.claimed, 0), func.coalesce(cards.c.respawning, 0))
        .join(photos, photos.c.spot_id == Spot.id, isouter=True)
        .join(cards, cards.c.spot_id == Spot.id, isouter=True)
        .order_by(Spot.created_at)
    )).all()
    return [
        {"id": s.id, "name": s.name, "lat": s.lat, "lng": s.lng, "is_active": s.is_active,
         "photos": p, "need": round(spot_need(p), 2),
         "cards_active": a, "cards_claimed": c, "cards_respawning": r}
        for s, p, a, c, r in rows
    ]


@router.post("/spots/{spot_id}/deactivate")
async def deactivate_spot(spot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    spot = await db.get(Spot, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    spot.is_active = False  # caught cards here stop respawning; cards already on the map stay
    await db.commit()
    return {"id": spot.id, "is_active": False}

'''Spots are the places cards respawn around. Creating a spot adopts existing unlinked cards within 15 m,
so cards placed earlier by hand (e.g. the beta cards) start respawning without being recreated.'''
