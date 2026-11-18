import math
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Card, Staff, Submission
from ..handoff import send_to_doskaz
from ..timeutil import to_local, utcnow_naive
from .auth import current_staff, require_role
from .routes import templates

# Show every stored (UTC) time in Almaty time: {{ sub.created_at | local }}
templates.env.filters["local"] = lambda dt, fmt="%d %b %Y, %H:%M": to_local(dt).strftime(fmt) if dt else "—"

router = APIRouter(prefix="/staff", tags=["staff pages"], include_in_schema=False)

PHOTO_DIR = Path("storage/photos").resolve()
FAR_METERS = 50  # a player further than this from the card is flagged in red

# The same six user groups doskaz uses, so accepted data can be handed over unchanged.
ACCESS_GROUPS = [
    ("movement", "Movement (wheelchair)"),
    ("limb", "Limbs (crutches, cane)"),
    ("vision", "Vision"),
    ("hearing", "Hearing"),
    ("intellectual", "Intellectual"),
    ("kids", "With kids (strollers)"),
]
ACCESS_VALUES = [("unknown", "Unknown"), ("full", "Full"), ("partial", "Partial"), ("no", "No")]
REJECT_REASONS = [
    ("blurry", "Blurry or too dark"),
    ("wrong_place", "Wrong place"),
    ("not_object", "Not the object"),
    ("privacy", "Faces or number plates visible"),
    ("inappropriate", "Inappropriate"),
    ("duplicate", "Duplicate"),
    ("other", "Other"),
]
STATUSES = ("pending", "accepted", "rejected")
DOSKAZ_DEFAULT_CATEGORY = 28  # the category used in the Phase 6 test; see /doskaz/categories for others


def photo_paths(sub: Submission) -> list[str]:
    """All photos of a submission. One for now; multi-photo submissions will extend this list."""
    return [sub.photo_path] if sub.photo_path else []


def access_summary(accessibility: dict | None) -> str:
    """Our reviewer's 6-group verdict as one line of text for doskaz's checker."""
    labels = dict(ACCESS_GROUPS)
    values = dict(ACCESS_VALUES)
    data = accessibility or {}
    return "; ".join(f"{labels[k]}: {values.get(data.get(k, 'unknown'), 'Unknown')}" for k, _ in ACCESS_GROUPS)


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle (haversine) distance in meters."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def row_view(sub: Submission, card: Card | None) -> dict:
    dist = distance_m(sub.lat, sub.lng, card.lat, card.lng) if card else None
    return {
        "sub": sub,
        "card": card,
        "player_short": str(sub.player_id)[:8],
        "distance": round(dist) if dist is not None else None,
        "far": dist is not None and dist > FAR_METERS,
    }


async def next_pending_id(db: AsyncSession, exclude_id=None):
    query = select(Submission.id).where(Submission.review_status == "pending")
    if exclude_id is not None:
        query = query.where(Submission.id != exclude_id)
    result = await db.execute(query.order_by(Submission.created_at).limit(1))
    return result.scalar_one_or_none()


@router.get("")
async def staff_home(staff: Staff = Depends(current_staff)):
    return RedirectResponse("/staff/queue", status_code=303)


@router.get("/queue")
async def queue(
    request: Request, status: str = "pending",
    staff: Staff = Depends(current_staff), db: AsyncSession = Depends(get_db),
):
    if status not in STATUSES:
        status = "pending"
    order = Submission.created_at if status == "pending" else Submission.reviewed_at.desc().nulls_last()
    result = await db.execute(
        select(Submission, Card).join(Card, Card.id == Submission.card_id, isouter=True)
        .where(Submission.review_status == status).order_by(order).limit(200)
    )
    rows = [row_view(sub, card) for sub, card in result.all()]
    counts = dict((await db.execute(
        select(Submission.review_status, func.count()).group_by(Submission.review_status)
    )).all())
    return templates.TemplateResponse(request, "staff/queue.html", {
        "staff": staff, "rows": rows, "status": status, "counts": counts, "statuses": STATUSES,
    })


@router.get("/submissions/{submission_id}")
async def review_page(
    request: Request, submission_id: str,
    staff: Staff = Depends(current_staff), db: AsyncSession = Depends(get_db),
):
    sub = await db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    card = await db.get(Card, sub.card_id)
    reviewer = await db.get(Staff, sub.reviewer_id) if sub.reviewer_id else None
    pending_left = (await db.execute(
        select(func.count()).where(Submission.review_status == "pending")
    )).scalar_one()
    return templates.TemplateResponse(request, "staff/review.html", {
        "staff": staff, **row_view(sub, card), "reviewer": reviewer,
        "access_groups": ACCESS_GROUPS, "access_values": ACCESS_VALUES,
        "reject_reasons": REJECT_REASONS, "saved_access": sub.accessibility or {},
        "next_id": await next_pending_id(db, exclude_id=sub.id), "pending_left": pending_left,
        "photo_count": len(photo_paths(sub)),
        "can_send": staff.role == "admin" and sub.review_status == "accepted"
                    and sub.handoff_status in ("held", "failed"),
        "default_category": DOSKAZ_DEFAULT_CATEGORY,
        "doskaz_result": request.query_params.get("doskaz"),
    })


@router.post("/submissions/{submission_id}/review")
async def save_review(
    request: Request, submission_id: str,
    decision: str = Form(...), reject_reason: str | None = Form(None),
    staff: Staff = Depends(current_staff), db: AsyncSession = Depends(get_db),
):
    sub = await db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if decision not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="Unknown decision")
    valid_reasons = {key for key, _ in REJECT_REASONS}
    if decision == "reject" and reject_reason not in valid_reasons:
        raise HTTPException(status_code=400, detail="Choose a reason to reject")

    form = await request.form()
    valid_values = {key for key, _ in ACCESS_VALUES}
    sub.accessibility = {
        key: form.get(f"access_{key}") if form.get(f"access_{key}") in valid_values else "unknown"
        for key, _ in ACCESS_GROUPS
    }
    sub.review_status = "accepted" if decision == "accept" else "rejected"
    sub.reject_reason = reject_reason if decision == "reject" else None
    sub.reviewer_id = staff.id
    sub.reviewed_at = utcnow_naive()
    await db.commit()

    next_id = await next_pending_id(db)
    return RedirectResponse(f"/staff/submissions/{next_id}" if next_id else "/staff/queue", status_code=303)


@router.post("/submissions/{submission_id}/send-to-doskaz")
async def send_submission_to_doskaz(
    submission_id: str,
    name: str = Form(...), address: str = Form("Алматы"), category_id: int = Form(DOSKAZ_DEFAULT_CATEGORY),
    staff: Staff = Depends(require_role("admin")), db: AsyncSession = Depends(get_db),
):
    sub = await db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.review_status != "accepted" or sub.handoff_status not in ("held", "failed"):
        raise HTTPException(status_code=400, detail="Only accepted submissions that were not sent yet")
    if not name.strip():
        raise HTTPException(status_code=400, detail="Object name is required")

    sub.handoff_status, _ = await send_to_doskaz(
        photo_paths=photo_paths(sub),
        name=name.strip(),
        description=f"Collected with Meme Hunter. Accessibility checked by our reviewer: {access_summary(sub.accessibility)}.",
        address=address.strip() or "Алматы",
        point=[sub.lat, sub.lng],
        category_id=category_id,
    )
    await db.commit()
    return RedirectResponse(f"/staff/submissions/{sub.id}?doskaz={sub.handoff_status}", status_code=303)


@router.get("/photos/{submission_id}")
async def photo(
    submission_id: str, i: int = 0,
    staff: Staff = Depends(current_staff), db: AsyncSession = Depends(get_db),
):
    sub = await db.get(Submission, submission_id)
    paths = photo_paths(sub) if sub else []
    if not 0 <= i < len(paths):
        raise HTTPException(status_code=404, detail="No photo")
    path = Path(paths[i]).resolve()
    if PHOTO_DIR not in path.parents or not path.is_file():  # only files inside storage/photos
        raise HTTPException(status_code=404, detail="No photo")
    return FileResponse(path, media_type="image/jpeg")


'''Reviewers see a short player number, never the player's name. Accepting or rejecting does not touch coins
(the base reward was paid on submission) and sends nothing to doskaz: handoff_status stays "held" until an admin
presses "Send to doskaz", which sends that one submission whatever DOSKAZ_HANDOFF_ENABLED says.
Saving a decision opens the oldest pending submission next, so a reviewer can work through the queue without going back.'''
