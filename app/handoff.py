import httpx

from .doskaz_client import DoskazClient


async def send_to_doskaz(
    photo_paths: list[str], name: str, description: str, address: str,
    point: list[float], category_id: int,
) -> tuple[str, str | None]:
    """Upload the photos and submit one facility request to doskaz.

    Returns ("sent", None) or ("failed", reason). Used both by the automatic handoff on submission
    (when DOSKAZ_HANDOFF_ENABLED is on) and by the admin's "Send to doskaz" button on the review page.
    Takes a list so multi-photo submissions can be sent later without changing callers.
    """
    doskaz = DoskazClient()
    try:
        uploaded = [await doskaz.upload_photo(path) for path in photo_paths]
        await doskaz.submit_facility(
            name=name, description=description, address=address,
            point=point, category_id=category_id, photo_paths=uploaded,
        )
        return "sent", None
    except httpx.HTTPStatusError as e:
        print("doskaz rejected the request:", e.request.url, e.response.status_code, e.response.text)
        return "failed", f"doskaz answered {e.response.status_code}"
    except httpx.HTTPError as e:
        print("could not reach doskaz:", repr(e))
        return "failed", "could not reach doskaz"
