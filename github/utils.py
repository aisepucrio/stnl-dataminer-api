from django.utils import timezone
from datetime import datetime
import pytz

class DateTimeHandler:
    @staticmethod
    def parse_date(date_str):
        if not date_str:
            return None
            
        try:
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            
            parsed_date = datetime.fromisoformat(date_str)
            
            if parsed_date.tzinfo is None:
                parsed_date = timezone.make_aware(parsed_date, timezone=pytz.UTC)
                
            return parsed_date
            
        except ValueError as e:
            raise ValueError(f"Formato de data inválido: {date_str}. Use o formato ISO (YYYY-MM-DDTHH:MM:SSZ)") from e
    
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