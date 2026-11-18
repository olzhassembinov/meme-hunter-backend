from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Staff
from .auth import current_staff, verify_password

router = APIRouter(prefix="/staff", tags=["staff pages"], include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "staff/login.html", {"error": None})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Staff).where(Staff.username == username.strip()))
    staff = result.scalar_one_or_none()
    if staff is None or not staff.is_active or not verify_password(password, staff.password_hash):
        return templates.TemplateResponse(
            request, "staff/login.html",
            {"error": "Wrong username or password", "username": username}, status_code=401,
        )
    request.session.clear()
    request.session["staff_id"] = str(staff.id)
    return RedirectResponse("/staff", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/staff/login", status_code=303)


'''One error message for "no such user" and "wrong password", so the page never reveals which usernames exist.
Redirects use 303 so the browser follows them with a GET after a form POST.'''
