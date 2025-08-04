import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Generator, Tuple


class APIMetrics:
    """Tracks API usage metrics and rate limits for GitHub API requests"""
    
    def __init__(self):
        self.execution_start = time.time()
        self.total_requests = 0
        self.total_prs_collected = 0
        self.pages_processed = 0
        # Core metrics
        self.core_limit_remaining = None
        self.core_limit_reset = None
        self.core_limit_limit = None
        # Search metrics
        self.search_limit_remaining = None
        self.search_limit_reset = None
        self.search_limit_limit = None
        self.requests_used = None
        self.average_time_per_request = 0
    
    def update_rate_limit(self, headers: dict, endpoint_type: str = 'core') -> None:
        """
        Updates rate limit information based on response headers
        
        Args:
            headers: Response headers from GitHub API
            endpoint_type: Type of endpoint being accessed ('core' or 'search')
        """
        if endpoint_type == 'search':
            self.search_limit_remaining = headers.get('X-RateLimit-Remaining')
            self.search_limit_reset = headers.get('X-RateLimit-Reset')
            self.search_limit_limit = headers.get('X-RateLimit-Limit', 30)  # Search has a limit of 30/min
            
            if self.search_limit_limit and self.search_limit_remaining:
                self.requests_used = int(self.search_limit_limit) - int(self.search_limit_remaining)
        else:  # core
            self.core_limit_remaining = headers.get('X-RateLimit-Remaining')
            self.core_limit_reset = headers.get('X-RateLimit-Reset')
            self.core_limit_limit = headers.get('X-RateLimit-Limit', 5000)  # Core has a limit of 5000/hour
            
            if self.core_limit_limit and self.core_limit_remaining:
                self.requests_used = int(self.core_limit_limit) - int(self.core_limit_remaining)
        
        if self.total_requests > 0:
            total_time = time.time() - self.execution_start
            self.average_time_per_request = total_time / self.total_requests

    def format_reset_time(self, endpoint_type: str = 'core') -> str:
        """Converts the Unix timestamp to a readable format considering the local timezone"""
        reset_time = self.core_limit_reset if endpoint_type == 'core' else self.search_limit_reset
        if reset_time:
            try:
                reset_time_utc = datetime.fromtimestamp(int(reset_time), tz=timezone.utc)
                reset_time_local = reset_time_utc.astimezone(timezone(timedelta(hours=-3)))  # Brasília timezone
                
                time_until_reset = reset_time_local - datetime.now().astimezone(timezone(timedelta(hours=-3)))
                seconds_until_reset = int(time_until_reset.total_seconds())
                
                return f"{reset_time_local.strftime('%Y-%m-%d %H:%M:%S')} (in {seconds_until_reset} seconds)"
            except Exception as e:
                print(f"Error formatting reset time: {e}")
                return "Unknown"
        return "Unknown"

    def get_remaining_requests(self, endpoint_type: str = 'core') -> Optional[str]:
        """Returns the number of remaining requests for the specified endpoint type"""
        return (self.core_limit_remaining if endpoint_type == 'core' 
                else self.search_limit_remaining)

    def get_execution_time(self) -> dict:
        """Calculates execution time metrics"""
        total_time = time.time() - self.execution_start
        return {
            "seconds": round(total_time, 2),
            "formatted": f"{int(total_time // 60)}min {int(total_time % 60)}s"
        }


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Remove or replace invalid characters from text"""
    if text is None:
        return None
    # Replace null characters with space
    return text.replace('\u0000', ' ')


def split_date_range(start_date: Optional[str], end_date: Optional[str], 
                    interval_days: int = 1) -> Generator[Tuple[str, str], None, None]:
    """
    Split the date range into smaller periods
    
    Args:
        start_date: Start date in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)
        end_date: End date in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)
        interval_days: Number of days per interval
        
    Yields:
        Tuples of (start_date, end_date) for each interval
    """
    if not start_date or not end_date:
        yield (start_date, end_date)
        return

    if isinstance(start_date, datetime):
        start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        
    if isinstance(end_date, datetime):
        end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S")

    start = datetime.strptime(start_date.rstrip('Z'), "%Y-%m-%dT%H:%M:%S")
    end = datetime.strptime(end_date.rstrip('Z'), "%Y-%m-%dT%H:%M:%S")
    
    current = start
    while current < end:
        interval_end = min(current + timedelta(days=interval_days), end)
        yield (
            current.strftime("%Y-%m-%d"),
            interval_end.strftime("%Y-%m-%d")
        )
        current = interval_end + timedelta(days=1)


def calculate_period_days(start_date: Optional[str], end_date: Optional[str]) -> int:
    """
    Calculates the number of days between two dates
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Number of days between the dates or "full period" string
    """
    if not start_date or not end_date:
        return "full period"
        
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return (end - start).days + 1


def convert_to_iso8601(date: datetime) -> str:
    """Convert datetime to ISO8601 format"""
    return date.isoformat() 