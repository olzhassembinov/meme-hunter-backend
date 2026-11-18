import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Staff


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


class LoginRequired(Exception):
    """Raised when a staff page is opened without a valid login; main.py turns it into a redirect."""


async def current_staff(request: Request, db: AsyncSession = Depends(get_db)) -> Staff:
    staff_id = request.session.get("staff_id")
    staff = await db.get(Staff, staff_id) if staff_id else None
    if staff is None or not staff.is_active:
        request.session.clear()
        raise LoginRequired()
    return staff


def require_role(*roles: str):
    """Dependency for pages only some roles may open, e.g. Depends(require_role("admin"))."""
    async def checker(staff: Staff = Depends(current_staff)) -> Staff:
        if staff.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for your role")
        return staff
    return checker

'''Login state lives in a signed cookie (SessionMiddleware in main.py): it only holds the staff id,
and the signature (SESSION_SECRET) stops anyone from forging it. Every page re-reads the staff row,
so disabling an account (is_active = false) logs that person out on their next click.'''
