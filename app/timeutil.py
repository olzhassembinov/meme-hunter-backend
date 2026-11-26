from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Almaty")


def utcnow_naive() -> datetime:
    """Current time in UTC without tzinfo: how every timestamp is stored in this database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_local(value: datetime | None) -> datetime | None:
    """Stored (naive UTC) timestamp -> Almaty time, for showing on staff pages."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)


def local_today(now_utc: datetime | None = None) -> date:
    """Calendar day in Almaty for a naive UTC moment (default: now). Daily streaks count Almaty days."""
    now_utc = now_utc or utcnow_naive()
    return now_utc.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).date()
