import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..admin_auth import require_admin
from ..database import get_db
from ..models import Card, Zone
from ..zones import ZONE_KINDS, in_active_zone, point, polygons_from_geojson

router = APIRouter(prefix="/admin", tags=["admin: zones & cards"], dependencies=[Depends(require_admin)])


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1)
    kind: str  # "restricted" or "dangerous"
    geojson: dict  # FeatureCollection from geojson.io, a Feature, or a Polygon/MultiPolygon geometry


class CardCreate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    rarity: str = "common"
    base_reward: int = 10
    bonus_reward: int = 20


async def deactivate_cards_inside(db: AsyncSession, zone_id) -> int:
    """Cards that are now inside a zone stop existing for players: active ones and claimed ones."""
    zone_area = select(Zone.area).where(Zone.id == zone_id).scalar_subquery()
    result = await db.execute(
        update(Card)
        .where(Card.status.in_(("active", "claimed")), func.ST_Intersects(zone_area, Card.location))
        .values(status="inactive")
    )
    return result.rowcount


@router.post("/zones")
async def create_zones(data: ZoneCreate, db: AsyncSession = Depends(get_db)):
    if data.kind not in ZONE_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {ZONE_KINDS}")
    try:
        shapes = polygons_from_geojson(data.geojson)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    created = []
    for i, shape in enumerate(shapes, start=1):
        name = data.name if len(shapes) == 1 else f"{data.name} #{i}"
        # ST_MakeValid repairs self-crossing shapes that hand drawing sometimes produces.
        area = func.ST_MakeValid(func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(shape)), 4326))
        zone = Zone(id=uuid.uuid4(), name=name, kind=data.kind, area=area, is_active=True)
        db.add(zone)
        await db.flush()
        removed = await deactivate_cards_inside(db, zone.id)
        created.append({"id": zone.id, "name": name, "kind": data.kind, "cards_deactivated": removed})
    await db.commit()
    return {"zones": created}


@router.get("/zones")
async def list_zones(include_inactive: bool = False, db: AsyncSession = Depends(get_db)):
    query = select(Zone, func.ST_AsGeoJSON(Zone.area)).order_by(Zone.created_at)
    if not include_inactive:
        query = query.where(Zone.is_active.is_(True))
    rows = (await db.execute(query)).all()
    return [
        {"id": z.id, "name": z.name, "kind": z.kind, "is_active": z.is_active,
         "created_at": z.created_at, "geometry": json.loads(geo)}
        for z, geo in rows
    ]


@router.post("/zones/{zone_id}/deactivate")
async def deactivate_zone(zone_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    zone = await db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    zone.is_active = False
    await db.commit()
    # Cards that were deactivated by this zone are not brought back automatically: create new ones if needed.
    return {"id": zone.id, "is_active": False}


@router.post("/cards")
async def create_card(data: CardCreate, db: AsyncSession = Depends(get_db)):
    blocked = (await db.execute(
        select(Zone.name, Zone.kind)
        .where(Zone.is_active.is_(True), func.ST_Intersects(Zone.area, point(data.lat, data.lng)))
        .limit(1)
    )).first()
    if blocked:
        raise HTTPException(status_code=409, detail=f"Point is inside {blocked.kind} zone '{blocked.name}'")
    card = Card(lat=data.lat, lng=data.lng, rarity=data.rarity,
                base_reward=data.base_reward, bonus_reward=data.bonus_reward, status="active")
    db.add(card)
    await db.commit()
    return {"id": card.id, "lat": card.lat, "lng": card.lng, "rarity": card.rarity, "status": card.status}

'''Admin-only (X-Admin-Key) tools for safety zones. A zone hides every card inside it at once and blocks new ones;
cards.location is computed by Postgres, so even cards inserted by hand with SQL are covered by the checks.'''
