"""Daily streak (Duolingo-style), counted on successful photo submissions, not on app opens.

Days are Almaty calendar days (see app/timeutil.local_today). All tunable numbers live here.
"""
from datetime import date

from .models import Player

FREEZE_PRICE = 40  # coins per streak freeze
FREEZE_MAX = 2  # how many freezes a player may hold at once


def apply_submission(player: Player, today: date) -> None:
    """Update the streak for a submission made today. One freeze covers one missed day."""
    last = player.last_active_date
    if last is None:
        player.current_streak = 1
    elif last >= today:
        return  # already counted today
    else:
        missed = (today - last).days - 1
        if missed == 0:
            player.current_streak += 1
        elif player.streak_freeze_count >= missed:
            player.streak_freeze_count -= missed
            player.current_streak += 1  # the freezes keep the streak alive, today extends it
        else:
            player.current_streak = 1  # not enough freezes: streak starts over, freezes are kept
    player.last_active_date = today


def effective_streak(player: Player, today: date) -> int:
    """Streak as the player sees it now. The stored value only changes on submission,
    so a streak that has already burned out (more missed days than freezes) is shown as 0."""
    last = player.last_active_date
    if last is None:
        return 0
    missed = (today - last).days - 1
    if missed <= 0 or missed <= player.streak_freeze_count:
        return player.current_streak
    return 0


def streak_state(player: Player, today: date) -> dict:
    return {
        "current_streak": effective_streak(player, today),
        "streak_freeze_count": player.streak_freeze_count,
        "streak_done_today": player.last_active_date == today,
    }
