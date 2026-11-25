"""Player progression: XP, ranks and the XP booster.

All tunable numbers live here. Rank is derived from xp and never stored in the database.
"""
from datetime import datetime, timedelta

from .models import Card, Player

XP_PER_COIN = 5  # a card's XP = its coin reward x 5 (common 10 coins -> 50 XP)

# (minimum xp, rank id). Rank ids are placeholders; display names are decided by the client.
RANK_THRESHOLDS = [
    (0, "rank_1"),
    (500, "rank_2"),
    (1500, "rank_3"),
    (3500, "rank_4"),
    (7000, "rank_5"),
]

BOOSTER_PRICES = {2: 50, 5: 150}  # multiplier -> price in coins
BOOSTER_DURATION = timedelta(hours=24)


def card_xp(card: Card) -> int:
    return card.base_reward * XP_PER_COIN


def rank_info(xp: int) -> tuple[str, int | None]:
    """Return (rank id, xp still needed for the next rank). The second value is None at the top rank."""
    current = RANK_THRESHOLDS[0][1]
    for minimum, rank in RANK_THRESHOLDS:
        if xp >= minimum:
            current = rank
        else:
            return current, minimum - xp
    return current, None


def active_multiplier(player: Player, now: datetime) -> int:
    if player.xp_booster_multiplier and player.xp_booster_expires_at and now < player.xp_booster_expires_at:
        return player.xp_booster_multiplier
    return 1


def booster_state(player: Player, now: datetime) -> dict:
    if active_multiplier(player, now) == 1:
        return {"active": False, "multiplier": None, "expires_at": None, "seconds_left": 0}
    return {
        "active": True,
        "multiplier": player.xp_booster_multiplier,
        "expires_at": player.xp_booster_expires_at.isoformat() + "Z",
        "seconds_left": int((player.xp_booster_expires_at - now).total_seconds()),
    }


def profile(player: Player, now: datetime) -> dict:
    """Player data as returned by GET /players/{id} and the booster purchase."""
    rank, to_next = rank_info(player.xp)
    return {
        "id": player.id,
        "display_name": player.display_name,
        "currency_balance": player.currency_balance,
        "level": player.level,
        "xp": player.xp,
        "rank": rank,
        "xp_to_next_rank": to_next,
        "booster": booster_state(player, now),
    }
