from sqlalchemy import and_, exists, func, select

from .models import Zone

ZONE_KINDS = ("restricted", "dangerous")


def in_active_zone(location_column):
    """SQL condition: true when the point lies inside (or on the edge of) any active zone."""
    return exists(
        select(Zone.id).where(and_(Zone.is_active.is_(True), func.ST_Intersects(Zone.area, location_column)))
    )


def point(lat: float, lng: float):
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)


def polygons_from_geojson(data: dict) -> list[dict]:
    """Accept what geojson.io gives (FeatureCollection), a single Feature, or a bare geometry.
    Returns the Polygon/MultiPolygon geometries found; anything else is an error."""
    kind = data.get("type")
    if kind == "FeatureCollection":
        geometries = [f.get("geometry") or {} for f in data.get("features", [])]
    elif kind == "Feature":
        geometries = [data.get("geometry") or {}]
    else:
        geometries = [data]
    if not geometries:
        raise ValueError("No shapes found. Draw at least one polygon.")
    for g in geometries:
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Only polygons can be zones, got {g.get('type') or 'nothing'}. "
                             "On geojson.io use the polygon or rectangle tool, not lines or points.")
    return geometries
