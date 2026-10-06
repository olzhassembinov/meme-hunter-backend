from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Player
from ..schemas import PlayerCreate, PlayerOut

router = APIRouter(prefix="/players", tags=["players"])


@router.post("", response_model=PlayerOut)
async def create_player(data: PlayerCreate, db: AsyncSession = Depends(get_db)):
    player = Player(display_name=data.display_name)
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


@router.get("/{player_id}", response_model=PlayerOut)
async def get_player(player_id: str, db: AsyncSession = Depends(get_db)):
    return await db.get(Player, player_id)