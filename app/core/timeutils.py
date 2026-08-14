# app/core/timeutils.py
#
# AttorneyAvailability / ConsultationSlot store a "wall-clock" time
# (e.g. 09:00) plus a separate timezone label (e.g. "Asia/Kolkata") — that
# combination IS a real, unambiguous point in time, it's just not stored
# as one. These two helpers convert between that stored form and a true
# UTC instant, and back into whatever timezone a specific viewer wants to
# see it in.
#
# Uses Python's built-in `zoneinfo` (no extra dependency needed — requires
# Python 3.9+, this project runs 3.12).

from __future__ import annotations

from datetime import date, time, datetime, timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "UTC"


def _safe_zone(tz_name: Optional[str]) -> ZoneInfo:
    """Falls back to UTC if the stored string isn't a real IANA zone name."""
    name = tz_name or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def to_utc(local_date: date, local_time: time, tz_name: str) -> datetime:
    """
    Combine a date + wall-clock time that is understood to be IN `tz_name`,
    and return the real UTC instant it represents.

    Example: to_utc(2026-08-17, time(9, 0), "Asia/Kolkata")
             -> 2026-08-17 03:30:00+00:00   (9am IST = 3:30am UTC)
    """
    tz = _safe_zone(tz_name)
    local_dt = datetime.combine(local_date, local_time, tzinfo=tz)
    return local_dt.astimezone(dt_timezone.utc)


def format_in_timezone(dt_utc: datetime, tz_name: Optional[str]) -> str:
    """
    Format a UTC instant for display in `tz_name`, with the zone's
    abbreviation attached so the reader always knows whose time this is.

    Example: format_in_timezone(<3:30am UTC>, "America/New_York")
             -> "Aug 16, 2026 at 11:30 PM EDT"
    """
    tz = _safe_zone(tz_name)
    local_dt = dt_utc.astimezone(tz)
    abbrev = local_dt.tzname() or (tz_name or DEFAULT_TIMEZONE)
    return f"{local_dt.strftime('%b %d, %Y')} at {local_dt.strftime('%I:%M %p')} {abbrev}"


def to_viewer_local(dt_utc: datetime, tz_name: Optional[str]) -> datetime:
    """
    Converts a stored UTC instant into a specific viewer's own local time.
    Returns a datetime object (not a string) so callers can format it
    however they need — e.g. book-page wants separate date/time strings,
    emails want one combined sentence (see format_in_timezone above).
    """
    tz = _safe_zone(tz_name)
    return dt_utc.astimezone(tz)