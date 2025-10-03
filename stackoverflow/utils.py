# C:\projects\aise\stnl-dataminer-api\stackoverflow\utils.py

from datetime import datetime
from django.utils import timezone
import pytz


class StackDateTimeHandler:
    @staticmethod
    def epoch_to_dt(sec):
        """
        Converte epoch (segundos desde 1970-01-01) em datetime UTC.
        """
        if sec is None:
            return None
        return datetime.fromtimestamp(int(sec), tz=timezone.utc)

    @staticmethod
    def parse_date(date_str):
        """
        Converte string ISO8601 em datetime com timezone UTC.
        Exemplo aceito: '2024-01-15T12:34:56Z'
        """
        if not date_str:
            return None

        try:
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"

            parsed_date = datetime.fromisoformat(date_str)

            if parsed_date.tzinfo is None:
                parsed_date = timezone.make_aware(parsed_date, timezone=pytz.UTC)

            return parsed_date
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_str}. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
            ) from e

    @staticmethod
    def format_date(date_obj):
        """
        Converte datetime em string ISO8601 com timezone UTC.
        """
        if not date_obj:
            return None

        if not timezone.is_aware(date_obj):
            date_obj = timezone.make_aware(date_obj, timezone=pytz.UTC)

        return date_obj.isoformat()

    @staticmethod
    def validate_date_range(start_date, end_date):
        """
        Valida se start_date <= end_date.
        """
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date must be before end date")
