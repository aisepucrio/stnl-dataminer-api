from django.utils import timezone
from datetime import datetime
import pytz

class DateTimeHandler:
    @staticmethod
    def parse_date(date_str):
        if date_str is None:
            return None

        if not isinstance(date_str, str):
            raise ValueError(f"Date must be a string, got {type(date_str).__name__}")

        if date_str.strip() == "":
            return None

        try:
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'

            parsed_date = datetime.fromisoformat(date_str)

            if parsed_date.tzinfo is None:
                parsed_date = timezone.make_aware(parsed_date, timezone=pytz.UTC)

            return parsed_date

        except ValueError as e:
            raise ValueError(
                f"Formato de data inválido: {date_str}. Use o formato ISO (ex: '2024-01-01T00:00:00Z')"
            ) from e

    @staticmethod
    def format_date(date_obj):
        if not date_obj:
            return None

        if not timezone.is_aware(date_obj):
            date_obj = timezone.make_aware(date_obj, timezone=pytz.UTC)

        return date_obj.isoformat()

    @staticmethod
    def validate_date_range(start_date, end_date):
        if start_date and end_date and start_date > end_date:
            raise ValueError("A data inicial deve ser anterior à data final")
