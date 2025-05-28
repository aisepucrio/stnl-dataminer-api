from datetime import datetime
import os
from dotenv import load_dotenv
from django.utils import timezone
from .functions.answer_fetcher import fetch_answers
from .models import StackAnswer

class StackOverflowMiner:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("STACK_API_KEY")
        self.access_token = os.getenv("STACK_ACCESS_TOKEN")
        
        if not self.api_key or not self.access_token:
            raise Exception("STACK_API_KEY and STACK_ACCESS_TOKEN must be set in .env file")
        
    def get_answers(self, site: str = "stackoverflow", start_date: str = None, end_date: str = None):
        """
        Fetch answers from Stack Overflow within a date range
        
        Args:
            site (str): The site to fetch from (e.g., 'stackoverflow')
            start_date (str, optional): Start date in ISO format (YYYY-MM-DD)
            end_date (str, optional): End date in ISO format (YYYY-MM-DD)
            
        Returns:
            list: List of answers
        """
        return fetch_answers(
            site=site,
            start_date=start_date,
            end_date=end_date,
            api_key=self.api_key,
            access_token=self.access_token
        ) 