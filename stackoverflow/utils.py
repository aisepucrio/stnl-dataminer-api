# stackoverflow/utils.py
from datetime import datetime, timezone as dt_timezone
from typing import Optional, Union

from django.utils import timezone
import pytz

Number = Union[int, float, str]


def epoch_to_dt(sec: Optional[Number]) -> Optional[datetime]:
    """
    Convert a Unix epoch (seconds, milliseconds, or nanoseconds) to an aware UTC datetime.
    Accepts int/float/str; returns None for None/empty/invalid values.
    """
    if sec is None:
        return None
    try:
        value = float(sec.strip()) if isinstance(sec, str) else float(sec)

        # Heuristics for common epoch units
        if value > 1e12:       # nanoseconds
            value /= 1e9
        elif value > 1e10:     # milliseconds
            value /= 1e3

        return datetime.fromtimestamp(value, tz=dt_timezone.utc)
    except Exception:
        return None


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO 8601 string into an aware UTC datetime.
    Accepts e.g. '2024-01-15T12:34:56Z' or with explicit offsets.
    """
    if not date_str:
        return None
    try:
        ds = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ds)
        if dt.tzinfo is None:
            dt = timezone.make_aware(dt, timezone=pytz.UTC)
        return dt.astimezone(dt_timezone.utc)
    except Exception as e:
        raise ValueError(f"Invalid date format: {date_str}. Use ISO 8601.") from e


def format_date(date_obj: Optional[datetime]) -> Optional[str]:
    """
    Convert a datetime to an ISO 8601 string in UTC (aware).
    """
    if not date_obj:
        return None
    if not timezone.is_aware(date_obj):
        date_obj = timezone.make_aware(date_obj, timezone=pytz.UTC)
    return date_obj.astimezone(dt_timezone.utc).isoformat()


def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> None:
    """
    Validate that start_date <= end_date when both are provided.
    """
    if start_date and end_date and start_date > end_date:
        raise ValueError("Start date must be before end date")


# Optional: keep a class wrapper for backward compatibility
class StackDateTimeHandler:
    epoch_to_dt = staticmethod(epoch_to_dt)
    parse_date = staticmethod(parse_date)
    format_date = staticmethod(format_date)
    validate_date_range = staticmethod(validate_date_range)


__all__ = [
    "epoch_to_dt",
    "parse_date",
    "format_date",
    "validate_date_range",
    "StackDateTimeHandler",
]
