from fastapi import APIRouter
from ..doskaz_client import DoskazClient

router = APIRouter(prefix="/doskaz", tags=["doskaz"])


@router.get("/categories")
async def doskaz_categories():
    client = DoskazClient()
    return await client.list_categories()

'''This route is a thin debug wrapper you'll likely delete later — its only purpose is to let Postman trigger DoskazClient without needing the rest of the submission pipeline built yet.'''