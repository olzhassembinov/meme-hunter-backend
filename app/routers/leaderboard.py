import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Player, Submission
from ..progression import rank_info

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
async def leaderboard(
    player_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    caught = (
        select(Submission.player_id, func.count().label("cards"))
        .where(Submission.review_status != "rejected")
        .group_by(Submission.player_id)
        .subquery()
    )
    ranked = (
        select(
            Player.id, Player.display_name, Player.xp,
            func.coalesce(caught.c.cards, 0).label("cards"),
            func.row_number().over(order_by=(Player.xp.desc(), Player.created_at.asc())).label("position"),
        )
        .join(caught, caught.c.player_id == Player.id, isouter=True)
        .subquery()
    )

    def entry(row) -> dict:
        rank, _ = rank_info(row.xp)
        return {"position": row.position, "display_name": row.display_name,
                "xp": row.xp, "rank": rank, "cards": row.cards}

    top = (await db.execute(select(ranked).order_by(ranked.c.position).limit(limit))).all()
    me = None
    if player_id is not None:
        row = (await db.execute(select(ranked).where(ranked.c.id == player_id))).first()
        me = entry(row) if row else None
    return {"top": [entry(r) for r in top], "me": me}

'''Ranking by XP (coins are spent on boosters, so they would punish spending). Ties: earlier registration first.
Player ids are never exposed here, only display names.'''
