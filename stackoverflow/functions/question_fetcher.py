import requests
from datetime import datetime
import time
import logging
from stackoverflow.models import StackQuestion, StackUser, StackAnswer, StackTag, StackComment# Import StackQuestion and StackUser models
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

def create_or_update_user(user_id, user_data):
    stack_user = None
    try:
        current_time = int(timezone.now().timestamp())
        stack_user, created = StackUser.objects.get_or_create(
        user_id=user_id,
        defaults={
            'display_name': user_data.get('display_name'),
            'reputation': user_data.get('reputation', 0),
            'profile_image': user_data.get('profile_image'),
            'user_type': user_data.get('user_type'),
            'is_employee': user_data.get('is_employee', False),
            'creation_date': user_data.get('creation_date'),
            'last_access_date': user_data.get('last_access_date'),
            'last_modified_date': user_data.get('last_modified_date'),
            'link': user_data.get('link'),
            'accept_rate': user_data.get('accept_rate'),
            'about_me': user_data.get('about_me'),
            'location': user_data.get('location'),
            'website_url': user_data.get('website_url'),
            'account_id': user_data.get('account_id'),
            'badge_counts': user_data.get('badge_counts'),
            'collectives': user_data.get('collectives'),
            'view_count': user_data.get('view_count', 0),
            'down_vote_count': user_data.get('down_vote_count', 0),
            'up_vote_count': user_data.get('up_vote_count', 0),
            'answer_count': user_data.get('answer_count', 0),
            'question_count': user_data.get('question_count', 0),
            'reputation_change_year': user_data.get('reputation_change_year', 0),
            'reputation_change_quarter': user_data.get('reputation_change_quarter', 0),
            'reputation_change_month': user_data.get('reputation_change_month', 0),
            'reputation_change_week': user_data.get('reputation_change_week', 0),
            'reputation_change_day': user_data.get('reputation_change_day', 0),
            'time_mined': None  # Set to null to indicate incomplete data
        }
        )
        if not created:
            # Update existing user fields if necessary (optional, but good practice)
            stack_user.display_name = user_data.get('display_name', stack_user.display_name)
            stack_user.reputation = user_data.get('reputation', stack_user.reputation)
            stack_user.profile_image = user_data.get('profile_image', stack_user.profile_image)
            stack_user.user_type = user_data.get('user_type', stack_user.user_type)
            stack_user.is_employee = user_data.get('is_employee', stack_user.is_employee)
            stack_user.creation_date = user_data.get('creation_date', stack_user.creation_date)
            stack_user.last_access_date = user_data.get('last_access_date', stack_user.last_access_date)
            stack_user.last_modified_date = user_data.get('last_modified_date', stack_user.last_modified_date)
            stack_user.link = user_data.get('link', stack_user.link)
            stack_user.accept_rate = user_data.get('accept_rate', stack_user.accept_rate)
            stack_user.about_me = user_data.get('about_me', stack_user.about_me)
            stack_user.location = user_data.get('location', stack_user.location)
            stack_user.website_url = user_data.get('website_url', stack_user.website_url)
            stack_user.account_id = user_data.get('account_id', stack_user.account_id)
            stack_user.badge_counts = user_data.get('badge_counts', stack_user.badge_counts)
            stack_user.collectives = user_data.get('collectives', stack_user.collectives)
            stack_user.view_count = user_data.get('view_count', stack_user.view_count)
            stack_user.down_vote_count = user_data.get('down_vote_count', stack_user.down_vote_count)
            stack_user.up_vote_count = user_data.get('up_vote_count', stack_user.up_vote_count)
            stack_user.answer_count = user_data.get('answer_count', stack_user.answer_count)
            stack_user.question_count = user_data.get('question_count', stack_user.question_count)
            stack_user.reputation_change_year = user_data.get('reputation_change_year', stack_user.reputation_change_year)
            stack_user.reputation_change_quarter = user_data.get('reputation_change_quarter', stack_user.reputation_change_quarter)
            stack_user.reputation_change_month = user_data.get('reputation_change_month', stack_user.reputation_change_month)
            stack_user.reputation_change_week = user_data.get('reputation_change_week', stack_user.reputation_change_week)
            stack_user.reputation_change_day = user_data.get('reputation_change_day', stack_user.reputation_change_day)
            stack_user.time_mined = None  # Set to null to indicate incomplete data
            stack_user.save()
    except Exception as e:
        logger.error(f"Error processing StackUser with ID {user_data}: {e}")
    return stack_user

def create_answer(answer_data, question, owner):
    answer, _ = StackAnswer.objects.get_or_create(
        answer_id=answer_data.get('answer_id'),
        defaults={
            'question': question,
            'body': answer_data.get('body'),
            'score': answer_data.get('score', 0),
            'comment_count': answer_data.get('comment_count', 0),
            'up_vote_count': answer_data.get('up_vote_count', 0),
            'down_vote_count': answer_data.get('down_vote_count', 0),
            'is_accepted': answer_data.get('is_accepted', False),
            'creation_date': answer_data.get('creation_date'),
            'content_license': answer_data.get('content_license'),
            'last_activity_date': answer_data.get('last_activity_date'),
            'owner': owner,
            'share_link': answer_data.get('share_link'),
            'body_markdown': answer_data.get('body_markdown'),
            'link': answer_data.get('link'),
            'title': answer_data.get('title'),
            'time_mined': int(time.time()),
        }
    )
    return answer

def create_comment(comment_data, parent, owner):
    # figure out which FK to set
    question_obj = parent if isinstance(parent, StackQuestion) else None
    answer_obj   = parent if isinstance(parent, StackAnswer)  else None

    comment, _ = StackComment.objects.get_or_create(
        comment_id=comment_data.get('comment_id'),
        defaults={
            'post_type':       comment_data.get('post_type'),
            'post_id':         comment_data.get('post_id'),
            'body':            comment_data.get('body'),
            'score':           comment_data.get('score', 0),
            'creation_date':   comment_data.get('creation_date'),
            'content_license': comment_data.get('content_license'),
            'edited':          comment_data.get('edited', False),
            'owner':           owner,
            'body_markdown':   comment_data.get('body_markdown'),
            'link':            comment_data.get('link'),
            'time_mined':      int(time.time()),
            'question':        question_obj,
            'answer':          answer_obj,
        }
    )
    return comment

def make_question_serializable(question_data, stack_user, question_tags):
    """Convert question data to JSON-serializable format"""
    return {
        'question_id': question_data['question_id'],
        'title': question_data.get('title'),
        'body': question_data.get('body'),
        'creation_date': question_data.get('creation_date'),
        'score': question_data.get('score', 0),
        'view_count': question_data.get('view_count', 0),
        'answer_count': question_data.get('answer_count', 0),
        'comment_count': question_data.get('comment_count', 0),
        'up_vote_count': question_data.get('up_vote_count', 0),
        'down_vote_count': question_data.get('down_vote_count', 0),
        'is_answered': question_data.get('is_answered', False),
        'accepted_answer_id': question_data.get('accepted_answer_id'),
        'tags': question_tags,
        'owner': {
            'user_id': stack_user.user_id if stack_user else None,
            'display_name': stack_user.display_name if stack_user else None,
            'reputation': stack_user.reputation if stack_user else None,
        } if stack_user else None,
        'share_link': question_data.get('share_link'),
        'body_markdown': question_data.get('body_markdown'),
        'link': question_data.get('link'),
        'favorite_count': question_data.get('favorite_count', 0),
        'content_license': question_data.get('content_license'),
        'last_activity_date': question_data.get('last_activity_date'),
        'time_mined': question_data.get('time_mined'),
    }

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
            # logger.info(f"API Response Data: {data}")
            
            if 'error_id' in data:
                raise Exception(f"API Error: {data.get('error_message', 'Unknown error')}")
            
            # Process questions
            for item in data.get('items', []):
                # ADD THIS PRINT STATEMENT
                print(f"=== Processing question {item['question_id']} ===")
                print(f"Tags from API: {item.get('tags', [])}")
                
                # Extract owner data and create/update user
                owner_data = item.get('owner', {})
                owner_id = owner_data.get('user_id')
                stack_user = None
                if owner_id:
                    stack_user = create_or_update_user(owner_id, owner_data)

                # Extract tags before creating question
                question_tags = item.get('tags', [])
                print(f"Extracted tags: {question_tags}")

                # Create question data
                question = {
                    'question_id': item['question_id'],
                    'title': item.get('title'),
                    'body': item.get('body'),
                    'creation_date': item.get('creation_date'),
                    'score': item.get('score', 0),
                    'view_count': item.get('view_count', 0),
                    'answer_count': item.get('answer_count', 0),
                    'comment_count': item.get('comment_count', 0),
                    'up_vote_count': item.get('up_vote_count', 0),
                    'down_vote_count': item.get('down_vote_count', 0),
                    'is_answered': item.get('is_answered', False),
                    'accepted_answer_id': item.get('accepted_answer_id'),
                    'owner': stack_user,
                    'share_link': item.get('share_link'),
                    'body_markdown': item.get('body_markdown'),
                    'link': item.get('link'),
                    'favorite_count': item.get('favorite_count', 0),
                    'content_license': item.get('content_license', None),
                    'last_activity_date': item.get('last_activity_date'),
                    'time_mined': int(time.time()),
                }

                # Create or update the question
                stack_question, created = StackQuestion.objects.get_or_create(
                    question_id=question['question_id'],
                    defaults=question
                )
                
                # Add question to return list
                serializable_question = make_question_serializable(question, stack_user, question_tags)
                questions.append(serializable_question)

                # Process comments for the question
                comments = item.get('comments', [])
                if comments:
                    for comment in comments:
                        comment_owner_data = comment.get('owner', {})
                        comment_owner_id = comment_owner_data.get('user_id')
                        comment_owner = None
                        if comment_owner_id:
                            comment_owner = create_or_update_user(comment_owner_id, comment_owner_data)
                        create_comment(comment, stack_question, comment_owner)

                # Process answers and their comments
                if item.get('is_answered'):
                    for answer in item.get('answers', []):
                        # Create/update answer owner
                        answer_owner_data = answer.get('owner', {})
                        answer_owner_id = answer_owner_data.get('user_id')
                        answer_owner = None
                        if answer_owner_id:
                            answer_owner = create_or_update_user(answer_owner_id, answer_owner_data)
                        
                        # Create answer
                        stack_answer = create_answer(answer, stack_question, answer_owner)
                        
                        # Process answer comments
                        answer_comments = answer.get('comments', [])
                        if answer_comments:
                            for comment in answer_comments:
                                comment_owner_data = comment.get('owner', {})
                                comment_owner_id = comment_owner_data.get('user_id')
                                comment_owner = None
                                if comment_owner_id:
                                    comment_owner = create_or_update_user(comment_owner_id, comment_owner_data)
                                create_comment(comment, stack_answer, comment_owner)

                # Process tags - ADD MORE PRINT STATEMENTS
                print(f"About to process {len(question_tags)} tags for question {question['question_id']}")
                tag_objs = []
                for tag_name in question_tags:
                    print(f"Processing tag: {tag_name}")
                    tag_obj, created = StackTag.objects.get_or_create(name=tag_name)
                    tag_objs.append(tag_obj)
                    print(f"Tag '{tag_name}' {'created' if created else 'already exists'}")

                # Assign tags to the question
                print(f"Assigning {len(tag_objs)} tags to question {question['question_id']}")
                try:
                    stack_question.tags.set(tag_objs)
                    print(f"SUCCESS: Assigned tags to question {question['question_id']}")
                except Exception as e:
                    print(f"ERROR: Failed to assign tags to question {question['question_id']}: {e}")
                    raise

                # ADD THIS: Check if the relationship was actually saved
                print(f"Verifying tag assignment for question {question['question_id']}")
                actual_tags = list(stack_question.tags.all())
                print(f"Actual tags in database: {[tag.name for tag in actual_tags]}")
            
            logger.info(f"Processed {len(data.get('items', []))} questions")
            print(f"=== Finished processing batch of questions ===")
            
            # has_more = data.get('has_more', False)
            # if has_more:
            #     params['page'] += 1
            #     time.sleep(1)  # Respect rate limits
            has_more = False
                
        except requests.exceptions.RequestException as e:
            print(f"REQUEST ERROR: {str(e)}")
            logger.error(f"Request error: {str(e)}")
            if 'rate limit' in str(e).lower():
                logger.info("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)  # Wait for rate limit to reset
                continue
            raise Exception(f"Failed to fetch questions: {str(e)}")
        except Exception as e:
            print(f"GENERAL ERROR: {str(e)}")
            raise
    
    logger.info(f"Total questions fetched: {len(questions)}")
    print(f"=== Total questions fetched: {len(questions)} ===")
    return questions 