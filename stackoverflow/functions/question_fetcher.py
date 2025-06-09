import requests
from datetime import datetime
import time
import logging
from stackoverflow.models import StackQuestion, StackUser # Import StackQuestion and StackUser models

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
                print(item)
                owner_data = item.get('owner', {})
                owner_id = owner_data.get('user_id')
                
                stack_user = None
                if owner_id:
                    try:
                        stack_user, created = StackUser.objects.get_or_create(
                            user_id=owner_id,
                            defaults={
                                'display_name': owner_data.get('display_name'),
                                'reputation': owner_data.get('reputation', 0),
                                'profile_image': owner_data.get('profile_image'),
                                'user_type': owner_data.get('user_type'),
                                'is_employee': owner_data.get('is_employee', False),
                                'creation_date': datetime.fromtimestamp(owner_data['creation_date']) if 'creation_date' in owner_data else None,
                                'last_access_date': datetime.fromtimestamp(owner_data['last_access_date']) if 'last_access_date' in owner_data else None,
                                'last_modified_date': datetime.fromtimestamp(owner_data['last_modified_date']) if 'last_modified_date' in owner_data else None,
                                'link': owner_data.get('link'),
                                'accept_rate': owner_data.get('accept_rate'),
                                'about_me': owner_data.get('about_me'),
                                'location': owner_data.get('location'),
                                'website_url': owner_data.get('website_url'),
                                'account_id': owner_data.get('account_id'),
                                'badge_counts': owner_data.get('badge_counts'),
                                'collectives': owner_data.get('collectives'),
                                'view_count': owner_data.get('view_count', 0),
                                'down_vote_count': owner_data.get('down_vote_count', 0),
                                'up_vote_count': owner_data.get('up_vote_count', 0),
                                'answer_count': owner_data.get('answer_count', 0),
                                'question_count': owner_data.get('question_count', 0),
                                'reputation_change_year': owner_data.get('reputation_change_year', 0),
                                'reputation_change_quarter': owner_data.get('reputation_change_quarter', 0),
                                'reputation_change_month': owner_data.get('reputation_change_month', 0),
                                'reputation_change_week': owner_data.get('reputation_change_week', 0),
                                'reputation_change_day': owner_data.get('reputation_change_day', 0),
                            }
                        )
                        if not created:
                            # Update existing user fields if necessary (optional, but good practice)
                            stack_user.display_name = owner_data.get('display_name', stack_user.display_name)
                            stack_user.reputation = owner_data.get('reputation', stack_user.reputation)
                            stack_user.profile_image = owner_data.get('profile_image', stack_user.profile_image)
                            stack_user.user_type = owner_data.get('user_type', stack_user.user_type)
                            stack_user.is_employee = owner_data.get('is_employee', stack_user.is_employee)
                            if 'creation_date' in owner_data: stack_user.creation_date = datetime.fromtimestamp(owner_data['creation_date'])
                            if 'last_access_date' in owner_data: stack_user.last_access_date = datetime.fromtimestamp(owner_data['last_access_date'])
                            if 'last_modified_date' in owner_data: stack_user.last_modified_date = datetime.fromtimestamp(owner_data['last_modified_date'])
                            stack_user.link = owner_data.get('link', stack_user.link)
                            stack_user.accept_rate = owner_data.get('accept_rate', stack_user.accept_rate)
                            stack_user.about_me = owner_data.get('about_me', stack_user.about_me)
                            stack_user.location = owner_data.get('location', stack_user.location)
                            stack_user.website_url = owner_data.get('website_url', stack_user.website_url)
                            stack_user.account_id = owner_data.get('account_id', stack_user.account_id)
                            stack_user.badge_counts = owner_data.get('badge_counts', stack_user.badge_counts)
                            stack_user.collectives = owner_data.get('collectives', stack_user.collectives)
                            stack_user.view_count = owner_data.get('view_count', stack_user.view_count)
                            stack_user.down_vote_count = owner_data.get('down_vote_count', stack_user.down_vote_count)
                            stack_user.up_vote_count = owner_data.get('up_vote_count', stack_user.up_vote_count)
                            stack_user.answer_count = owner_data.get('answer_count', stack_user.answer_count)
                            stack_user.question_count = owner_data.get('question_count', stack_user.question_count)
                            stack_user.reputation_change_year = owner_data.get('reputation_change_year', stack_user.reputation_change_year)
                            stack_user.reputation_change_quarter = owner_data.get('reputation_change_quarter', stack_user.reputation_change_quarter)
                            stack_user.reputation_change_month = owner_data.get('reputation_change_month', stack_user.reputation_change_month)
                            stack_user.reputation_change_week = owner_data.get('reputation_change_week', stack_user.reputation_change_week)
                            stack_user.reputation_change_day = owner_data.get('reputation_change_day', stack_user.reputation_change_day)
                            stack_user.save()
                    except Exception as e:
                        logger.error(f"Error processing StackUser with ID {owner_id}: {e}")
                
                question = {
                    'question_id': item['question_id'],
                    'title': item.get('title'),
                    'body': item.get('body'),
                    'creation_date': datetime.fromtimestamp(item['creation_date']).isoformat() if 'creation_date' in item else None,
                    'score': item.get('score', 0),
                    'view_count': item.get('view_count', 0),
                    'answer_count': item.get('answer_count', 0),
                    'comment_count': item.get('comment_count', 0),
                    'up_vote_count': item.get('up_vote_count', 0),
                    'down_vote_count': item.get('down_vote_count', 0),
                    'tags': item.get('tags', []),
                    'is_answered': item.get('is_answered', False),
                    'accepted_answer_id': item.get('accepted_answer_id'),
                    'owner': stack_user,  # Assign the StackUser object
                    'share_link': item.get('share_link'),
                    'body_markdown': item.get('body_markdown'),
                    'link': item.get('link'),
                    'favorite_count': item.get('favorite_count', 0),
                    'content_license': item.get('content_license', None),
                    'last_activity_date': datetime.fromtimestamp(item['last_activity_date']).isoformat() if 'last_activity_date' in item else None,
                    'time_mined': datetime.now().isoformat(),
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