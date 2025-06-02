import requests
from datetime import datetime
import time
from typing import Optional, List, Dict, Any
from django.utils import timezone

# Constants
FILTER = "!)Rm-Ag_ZixQvpDE.3s.paOrN"
BASE_URL = "https://api.stackexchange.com/2.3"

class StackExchangeAPIError(Exception):
    """Custom exception for Stack Exchange API errors"""
    pass

def fetch_answers(
    site: str = "stackoverflow",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: str = None,
    access_token: str = None,
    page: int = 1,
    page_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch answers from Stack Exchange API within a date range
    
    Args:
        site (str): The site to fetch from, default = stackoverflow
        start_date (str, optional): Start date in ISO format (YYYY-MM-DD)
        end_date (str, optional): End date in ISO format (YYYY-MM-DD)
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        page (int): Page number for pagination (default: 1)
        page_size (int): Number of items per page (default: 100, max: 100)
        
    Returns:
        List[Dict[str, Any]]: List of answers with their details
        
    Raises:
        StackExchangeAPIError: If there's an error with the API request
        ValueError: If the date format is invalid
    """
    if not api_key or not access_token:
        raise StackExchangeAPIError("API key and access token are required")
    
    # Validate and convert dates
    try:
        from_date = int(datetime.fromisoformat(start_date).timestamp()) if start_date else None
        to_date = int(datetime.fromisoformat(end_date).timestamp()) if end_date else None
    except ValueError as e:
        raise ValueError(f"Invalid date format: {str(e)}")
    
    try:
        # Construct the API URL
        url = f"{BASE_URL}/answers"
        params = {
            'site': site,
            'page': page,
            'pagesize': min(page_size, 100),  # Stack Exchange API max is 100
            'fromdate': from_date,
            'todate': to_date,
            'order': 'desc',
            'sort': 'creation',
            'filter': FILTER,
            'key': api_key,
            'access_token': access_token
        }
        
        # Make the API request
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if 'error_id' in data:
            error_message = data.get('error_message', 'Unknown API error')
            if 'rate limit' in error_message.lower():
                raise StackExchangeAPIError("Rate limit exceeded. Please try again later.")
            raise StackExchangeAPIError(f"API Error: {error_message}")
        
        # Process the answers
        answers = []
        for answer in data.get('items', []):
            answer_data = {
                'answer_id': answer.get('answer_id'),
                'question_id': answer.get('question_id'),
                'body': answer.get('body'),
                'score': answer.get('score'),
                'comment_count': answer.get('comment_count', 0),
                'up_vote_count': answer.get('up_vote_count', 0),
                'down_vote_count': answer.get('down_vote_count', 0),
                'is_accepted': answer.get('is_accepted', False),
                'creation_date': datetime.fromtimestamp(answer.get('creation_date')),
                'content_license': answer.get('content_license'),
                'last_activity_date': datetime.fromtimestamp(answer.get('last_activity_date')),
                'owner': {
                    'user_id': answer.get('owner', {}).get('user_id'),
                    'display_name': answer.get('owner', {}).get('display_name'),
                    'reputation': answer.get('owner', {}).get('reputation'),
                },
                'share_link': answer.get('share_link'),
                'body_markdown': answer.get('body_markdown'),
                'link': answer.get('link'),
                'title': answer.get('title'),
                'time_mined': timezone.now()
            }
            answers.append(answer_data)
        
        return answers
        
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 429:
            raise StackExchangeAPIError("Rate limit exceeded. Please try again later.")
        raise StackExchangeAPIError(f"API request failed: {str(e)}")
    except Exception as e:
        raise StackExchangeAPIError(f"Unexpected error: {str(e)}") 