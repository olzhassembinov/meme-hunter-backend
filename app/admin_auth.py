from fastapi import Header, HTTPException
from .config import settings


async def require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
