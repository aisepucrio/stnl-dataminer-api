import requests
from datetime import datetime
import time
from typing import Optional, List, Dict, Any
from django.utils import timezone

# Constants
FILTER = "!)Rm-Ag_ZixQvpDE.3s.paOrN"
PAGE_SIZE = 100
BASE_URL = "https://api.stackexchange.com/2.3"

def fetch_answers(
    site: str = "stackoverflow",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: str = None,
    access_token: str = None
) -> List[Dict[str, Any]]:
    """
    Fetch answers from Stack Exchange API within a date range
    
    Args:
        site (str): The site to fetch from, default = stackoverflow
        start_date (str, optional): Start date in ISO format (YYYY-MM-DD)
        end_date (str, optional): End date in ISO format (YYYY-MM-DD)
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        List[Dict[str, Any]]: List of answers with their details
    """
    if not api_key or not access_token:
        raise Exception("API key and access token are required")
    
    all_answers = []
    page = 1
    has_more = True
    
    # Convert dates to Unix timestamps if provided
    from_date = int(datetime.fromisoformat(start_date).timestamp()) if start_date else None
    to_date = int(datetime.fromisoformat(end_date).timestamp()) if end_date else None
    
    while has_more:
        try:
            # Construct the API URL
            url = f"{BASE_URL}/answers"
            params = {
                'site': site,
                'page': page,
                'pagesize': PAGE_SIZE,
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
            
            # Process the answers
            for answer in data.get('items', []):
                answer_data = {
                    'answer_id': answer.get('answer_id'),
                    'question_id': answer.get('question_id'),  # This will be used to create the ForeignKey
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
                all_answers.append(answer_data)
            
            # Check if there are more pages
            has_more = data.get('has_more', False)
            page += 1
            
            # Respect API rate limits
            if 'backoff' in data:
                time.sleep(data['backoff'])
            else:
                time.sleep(1)  # Default delay between requests
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching answers: {str(e)}")
            break
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            break
    
    return all_answers 