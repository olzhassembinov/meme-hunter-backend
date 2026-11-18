"""Create a staff account (admin or reviewer) from the terminal.

Usage, from the backend folder with the virtualenv active:
    python -m scripts.create_staff <username> <admin|reviewer>
The password is asked twice and never shown or stored in plain text.
"""
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.database import async_session, engine
from app.models import Staff
from app.staff.auth import hash_password

ROLES = ("admin", "reviewer")


async def main(username: str, role: str, password: str) -> None:
    async with async_session() as db:
        exists = await db.execute(select(Staff).where(Staff.username == username))
        if exists.scalar_one_or_none():
            sys.exit(f"User '{username}' already exists.")
        db.add(Staff(username=username, password_hash=hash_password(password), role=role))
        await db.commit()
    await engine.dispose()
    print(f"Created {role} '{username}'.")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ROLES:
        sys.exit("Usage: python -m scripts.create_staff <username> <admin|reviewer>")
    username, role = sys.argv[1].strip(), sys.argv[2]
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        sys.exit("Use at least 8 characters.")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    asyncio.run(main(username, role, password))
