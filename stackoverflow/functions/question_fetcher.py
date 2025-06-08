import requests
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

def fetch_questions(site: str, start_date: str, end_date: str, api_key: str, access_token: str, page: int = 1, page_size: int = 100):
    """
    Fetch questions from Stack Overflow within a date range
    
    Args:
        site (str): The site to fetch from (e.g., 'stackoverflow')
        start_date (str): Start date in ISO format (YYYY-MM-DD)
        end_date (str): End date in ISO format (YYYY-MM-DD)
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        page (int, optional): Page number for pagination (default: 1)
        page_size (int, optional): Number of items per page (default: 100, max: 100)
        
    Returns:
        list: List of questions
    """
    base_url = f"https://api.stackexchange.com/2.3/questions"
    
    # Convert dates to Unix timestamps
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_timestamp = int(datetime.combine(start_dt.date(), datetime.min.time()).timestamp())
    end_timestamp = int(datetime.combine(end_dt.date(), datetime.max.time()).timestamp())
    
    logger.info(f"Fetching questions from {start_date} to {end_date}")
    logger.info(f"Timestamps: {start_timestamp} to {end_timestamp}")
    
    # Construct the API request
    params = {
        'site': site,
        'fromdate': start_timestamp,
        'todate': end_timestamp,
        'page': page,
        'pagesize': min(page_size, 100),  # API limit is 100
        'order': 'desc',
        'sort': 'creation',
        'filter': '!2xWEp6FHz8hT56C1LBQjFx25D4Dzmr*3(8D4ngdB5g',  # Beast filter
        'key': api_key,
        'access_token': access_token
    }
    
    logger.info(f"API Request URL: {base_url}")
    logger.info(f"API Request Params: {params}")
    
    questions = []
    has_more = True
    
    while has_more:
        try:
            response = requests.get(base_url, params=params)
            logger.info(f"API Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"API Response Data: {data}")
            
            if 'error_id' in data:
                raise Exception(f"API Error: {data.get('error_message', 'Unknown error')}")
            
            # Process questions
            for item in data.get('items', []):
                question = {
                    'question_id': item['question_id'],
                    'title': item['title'],
                    'body': item['body'],
                    'creation_date': datetime.fromtimestamp(item['creation_date']).isoformat(),
                    'score': item['score'],
                    'view_count': item['view_count'],
                    'answer_count': item['answer_count'],
                    # 'tags': item['tags'],
                    'is_answered': item['is_answered'],
                    # 'accepted_answer_id': item.get('accepted_answer_id'),  # Commented out to avoid error
                    'owner': item['owner'].get('user_id') if 'owner' in item else None
                }
                questions.append(question)
            
            logger.info(f"Processed {len(data.get('items', []))} questions")
            
            # has_more = data.get('has_more', False)
            # if has_more:
            #     params['page'] += 1
            #     time.sleep(1)  # Respect rate limits
            has_more = False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if 'rate limit' in str(e).lower():
                logger.info("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)  # Wait for rate limit to reset
                continue
            raise Exception(f"Failed to fetch questions: {str(e)}")
    
    logger.info(f"Total questions fetched: {len(questions)}")
    return questions 