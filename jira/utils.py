from datetime import datetime, timezone, timedelta
from typing import Optional, Generator, Tuple


def split_date_range(start_date: Optional[str], end_date: Optional[str], 
                     interval_days: int = 1) -> Generator[Tuple[str, str], None, None]:
    """
    Split a date range into daily (or custom) intervals.

    Args:
        start_date: Start date in ISO8601 or YYYY-MM-DD format
        end_date: End date in ISO8601 or YYYY-MM-DD format
        interval_days: Number of days per interval

    Yields:
        Tuples of (start_date, end_date) in YYYY-MM-DD
    """
    if not start_date or not end_date:
        yield (start_date, end_date)
        return

    if isinstance(start_date, datetime):
        start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")

    if isinstance(end_date, datetime):
        end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S")

    # Accept both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS
    def _parse_date(s: str) -> datetime:
        s = s.rstrip('Z')
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        # Fallback: try date only component
        return datetime.strptime(s[:10], "%Y-%m-%d")

    start = _parse_date(start_date)
    end = _parse_date(end_date)

    current = start
    while current < end:
        interval_end = min(current + timedelta(days=interval_days), end)
        yield (
            current.strftime("%Y-%m-%d"),
            interval_end.strftime("%Y-%m-%d")
        )
        current = interval_end + timedelta(days=1)


def update_task_progress_date(task_obj, completed_date: str) -> None:
    """
    Update Task.date_last_update to mark a completed day.

    Args:
        task_obj: Task instance to update
        completed_date: Date string in YYYY-MM-DD format
    """
    if not task_obj or not completed_date:
        return
    try:
        completed_datetime = datetime.strptime(completed_date, "%Y-%m-%d")
        completed_datetime = completed_datetime.replace(tzinfo=timezone.utc)
        task_obj.date_last_update = completed_datetime
        task_obj.save(update_fields=["date_last_update"])
        print(f" Progress tracked (Jira): Completed scraping for {completed_date}", flush=True)
    except Exception as e:
        print(f" Warning (Jira): Could not update progress date: {str(e)}", flush=True)
