"""Pure daily check-in rules (parent spec §3.4): calendar days in the practice timezone."""
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo


def local_date(at: datetime, tz_name: str) -> date:
    return at.astimezone(ZoneInfo(tz_name)).date()


def current_streak(dates: Iterable[date], today: date) -> int:
    days = set(dates)
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak
