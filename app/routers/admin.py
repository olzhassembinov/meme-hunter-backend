from datetime import datetime, timezone
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db, async_session
from ..models import Submission, PendingBonus, Player
from ..admin_auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/submissions")
async def list_submissions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission))
    return result.scalars().all()


@router.post("/submissions/{submission_id}/review")
async def review_submission(
    submission_id: str, decision: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    submission = await db.get(Submission, submission_id)
    submission.review_status = decision
    await db.commit()

    if decision == "accepted":
        background_tasks.add_task(credit_pending_bonus, submission_id)

    return {"submission_id": submission_id, "review_status": decision}


async def credit_pending_bonus(submission_id: str):
    async with async_session() as db:
        result = await db.execute(select(PendingBonus).where(PendingBonus.submission_id == submission_id))
        bonus = result.scalar_one_or_none()
        if not bonus or bonus.status != "pending":
            return

        submission = await db.get(Submission, submission_id)
        player = await db.get(Player, submission.player_id)
        player.currency_balance += bonus.amount
        bonus.status = "credited"
        bonus.credited_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
