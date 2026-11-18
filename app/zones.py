from sqlalchemy import and_, exists, func, select

from .models import Zone

BLOCKING_KINDS = ("restricted", "dangerous")  # no cards inside these
PLAY_AREA = "play_area"  # if any active play area exists, cards may exist only inside one
ZONE_KINDS = BLOCKING_KINDS + (PLAY_AREA,)


def _active(kinds):
    return and_(Zone.is_active.is_(True), Zone.kind.in_(kinds))


def in_active_zone(location_column):
    """SQL condition: true when the point lies inside (or on the edge of) an active restricted/dangerous zone."""
    return exists(select(Zone.id).where(_active(BLOCKING_KINDS), func.ST_Intersects(Zone.area, location_column)))


def outside_play_area(location_column):
    """SQL condition: true when play areas exist and the point is in none of them.
    With no active play area at all, the whole map is open (false for every point)."""
    any_play_area = exists(select(Zone.id).where(_active((PLAY_AREA,))))
    inside_one = exists(
        select(Zone.id).where(_active((PLAY_AREA,)), func.ST_Intersects(Zone.area, location_column))
    )
    return and_(any_play_area, ~inside_one)


def not_allowed(location_column):
    """SQL condition: a card at this point must not exist for players (blocked zone or outside the play area)."""
    return in_active_zone(location_column) | outside_play_area(location_column)


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
