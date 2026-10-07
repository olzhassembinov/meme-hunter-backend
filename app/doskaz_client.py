import httpx
import secrets
from .config import settings

# Attribute keys per zone, copied from a real doskaz "small form" submission (category 28).
# Every value is sent as "not_provided", same as a human skipping the section.
ZONE_ATTRIBUTES = {
    "parking": ["attribute1"],
    "entrance1": ["attribute1", "attribute1000", "attribute1001", "attribute30", "attribute31", "attribute1002"],
    "movement": ["attribute1", "attribute6", "attribute7", "attribute1000", "attribute1001"],
    "service": ["attribute1000"],
    "toilet": ["attribute1000"],
    "navigation": ["attribute1000"],
    "serviceAccessibility": ["attribute2"],
    "kidsAccessibility": ["attribute1"],
}


class DoskazClient:
    def __init__(self):
        self._base = settings.doskaz_base_url
        # doskaz's CSRF check: the X-Xsrf-Token header must equal the XSRF-TOKEN cookie.
        # Any random value works (verified with curl).
        xsrf = secrets.token_hex(16)
        self._cookies = {"ACCESS_TOKEN": settings.doskaz_access_token, "XSRF-TOKEN": xsrf}
        self._headers = {"X-Xsrf-Token": xsrf}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base, cookies=self._cookies, headers=self._headers, timeout=30
        )

    async def list_categories(self):
        async with self._client() as client:
            response = await client.get("/api/objects/categories")
            response.raise_for_status()
            return response.json()

    async def upload_photo(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            data = f.read()
        async with self._client() as client:
            response = await client.post(
                "/api/storage/upload",
                content=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},  # same as the browser
            )
            response.raise_for_status()
            return response.json()["path"]  # e.g. "/storage/74d6....jpeg"

    async def submit_facility(self, name, description, address, point, category_id, photo_paths):
        payload = {
            "form": "small",
            "first": {
                "categoryId": category_id,
                "videos": [""],
                "photos": photo_paths,
                "otherNames": name,
                "name": name,
                "point": point,  # [lat, lng]
                "address": address,
                "description": description,
            },
            "entrance2": None,
            "entrance3": None,
        }
        for zone, keys in ZONE_ATTRIBUTES.items():
            payload[zone] = {"attributes": {k: "not_provided" for k in keys}, "comment": ""}

        async with self._client() as client:
            response = await client.post("/api/objects/requests", json=payload)
            response.raise_for_status()  # success = 204 No Content, so there is nothing to parse