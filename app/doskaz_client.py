import httpx
from .config import settings


class DoskazClient:
    def __init__(self):
        self._base = settings.doskaz_base_url
        self._headers = {"Authorization": f"Bearer {settings.doskaz_access_token}"}

    async def list_categories(self):
        async with httpx.AsyncClient(base_url=self._base, headers=self._headers) as client:
            response = await client.get("/api/objects/categories")
            response.raise_for_status()
            return response.json()

'''One class, reused for every doskaz call across this guide — a single place to hold the base URL and auth header. list_categories is the smallest possible proof of connectivity: it's a real doskaz endpoint, it requires nothing from the game side to test, and a successful response means the token in .env is genuinely valid.'''