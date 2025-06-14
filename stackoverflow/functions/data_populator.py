import requests
import time
import logging
from django.utils import timezone
from django.db.models import Q
from stackoverflow.models import (
    StackUser, StackBadge, StackCollective, StackUserBadge,
    StackCollectiveUser, StackCollectiveTag, StackTag
)

logger = logging.getLogger(__name__)

def fetch_user_data(user_id: int, api_key: str, access_token: str) -> dict:
    """
    Fetch complete user data from Stack Exchange API
    
    Args:
        user_id (int): The ID of the user to fetch
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        dict: Complete user data
    """
    base_url = f"https://api.stackexchange.com/2.3/users/{user_id}"
    
    params = {
        'site': 'stackoverflow',
        'key': api_key,
        'access_token': access_token,
        'filter': '!6WPIommryG6wE'  # Filter for user data
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('items'):
            logger.error(f"No user data found for user_id: {user_id}")
            return None
            
        return data['items'][0]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching user data for user_id {user_id}: {str(e)}")
        return None

def fetch_user_badges(user_id: int, api_key: str, access_token: str) -> list:
    """
    Fetch user badges from Stack Exchange API
    
    Args:
        user_id (int): The ID of the user to fetch badges for
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        list: List of user badges
    """
    base_url = f"https://api.stackexchange.com/2.3/users/{user_id}/badges"
    
    params = {
        'site': 'stackoverflow',
        'key': api_key,
        'access_token': access_token,
        'filter': '!6WPIommryG6wE'  # Filter for badge data
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('items'):
            logger.error(f"No badges found for user_id: {user_id}")
            return []
            
        return data['items']
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching badges for user_id {user_id}: {str(e)}")
        return []

def fetch_collective_data(collective_id: str, api_key: str, access_token: str) -> dict:
    """
    Fetch collective data from Stack Exchange API
    
    Args:
        collective_id (str): The ID of the collective to fetch
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        dict: Complete collective data
    """
    base_url = f"https://api.stackexchange.com/2.3/collectives/{collective_id}"
    
    params = {
        'site': 'stackoverflow',
        'key': api_key,
        'access_token': access_token,
        'filter': '!6WPIommryG6wE'  # Filter for collective data
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('items'):
            logger.error(f"No collective data found for collective_id: {collective_id}")
            return None
            
        return data['items'][0]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching collective data for collective_id {collective_id}: {str(e)}")
        return None

def is_user_data_complete(user: StackUser) -> bool:
    """
    Check if a user has complete data
    
    Args:
        user (StackUser): The user to check
        
    Returns:
        bool: True if user data is complete, False otherwise
    """
    # Check essential fields that should be present for a complete user
    essential_fields = [
        'display_name', 'reputation', 'user_type', 'creation_date',
        'last_access_date', 'link', 'about_me', 'location', 'website_url',
        'account_id', 'badge_counts', 'collectives'
    ]
    
    return all(getattr(user, field) is not None for field in essential_fields)

def get_users_with_incomplete_data():
    """
    Get users that have incomplete data
    
    Returns:
        QuerySet: Users with incomplete data
    """
    return StackUser.objects.filter(
        Q(display_name__isnull=True) |
        Q(reputation__isnull=True) |
        Q(user_type__isnull=True) |
        Q(creation_date__isnull=True) |
        Q(last_access_date__isnull=True) |
        Q(link__isnull=True) |
        Q(about_me__isnull=True) |
        Q(location__isnull=True) |
        Q(website_url__isnull=True) |
        Q(account_id__isnull=True) |
        Q(badge_counts__isnull=True) |
        Q(collectives__isnull=True)
    )

def get_users_to_update():
    """
    Get users that need to be updated based on time_mined field
    
    Returns:
        QuerySet: Users that need updating
    """
    current_time = int(timezone.now().timestamp())
    week_in_seconds = 7 * 24 * 60 * 60  # 7 days in seconds
    
    return StackUser.objects.filter(
        Q(time_mined__isnull=True) |  # Never mined
        Q(time_mined__lt=current_time - week_in_seconds)  # Mined more than a week ago
    )

def update_user_data(user: StackUser, api_key: str, access_token: str) -> bool:
    """
    Update user data with complete information from Stack Exchange API
    
    Args:
        user (StackUser): The user object to update
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    user_data = fetch_user_data(user.user_id, api_key, access_token)
    if not user_data:
        return False
        
    # Update user fields
    user.display_name = user_data.get('display_name', user.display_name)
    user.reputation = user_data.get('reputation', user.reputation)
    user.profile_image = user_data.get('profile_image', user.profile_image)
    user.user_type = user_data.get('user_type', user.user_type)
    user.is_employee = user_data.get('is_employee', user.is_employee)
    user.creation_date = user_data.get('creation_date', user.creation_date)
    user.last_access_date = user_data.get('last_access_date', user.last_access_date)
    user.last_modified_date = user_data.get('last_modified_date', user.last_modified_date)
    user.link = user_data.get('link', user.link)
    user.accept_rate = user_data.get('accept_rate', user.accept_rate)
    user.about_me = user_data.get('about_me', user.about_me)
    user.location = user_data.get('location', user.location)
    user.website_url = user_data.get('website_url', user.website_url)
    user.account_id = user_data.get('account_id', user.account_id)
    user.badge_counts = user_data.get('badge_counts', user.badge_counts)
    user.collectives = user_data.get('collectives', user.collectives)
    user.view_count = user_data.get('view_count', user.view_count)
    user.down_vote_count = user_data.get('down_vote_count', user.down_vote_count)
    user.up_vote_count = user_data.get('up_vote_count', user.up_vote_count)
    user.answer_count = user_data.get('answer_count', user.answer_count)
    user.question_count = user_data.get('question_count', user.question_count)
    user.reputation_change_year = user_data.get('reputation_change_year', user.reputation_change_year)
    user.reputation_change_quarter = user_data.get('reputation_change_quarter', user.reputation_change_quarter)
    user.reputation_change_month = user_data.get('reputation_change_month', user.reputation_change_month)
    user.reputation_change_week = user_data.get('reputation_change_week', user.reputation_change_week)
    user.reputation_change_day = user_data.get('reputation_change_day', user.reputation_change_day)
    user.time_mined = int(timezone.now().timestamp())  # Update time_mined when data is fetched
    
    user.save()
    return True

def update_user_badges(user: StackUser, api_key: str, access_token: str) -> bool:
    """
    Update user badges with complete information from Stack Exchange API
    
    Args:
        user (StackUser): The user object to update badges for
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    badges_data = fetch_user_badges(user.user_id, api_key, access_token)
    if not badges_data:
        return False
        
    for badge_data in badges_data:
        badge, _ = StackBadge.objects.get_or_create(
            badge_id=badge_data['badge_id'],
            defaults={
                'name': badge_data['name'],
                'badge_type': badge_data['badge_type'],
                'rank': badge_data['rank'],
                'link': badge_data['link'],
                'description': badge_data['description']
            }
        )
        
        # Update badge if it already exists
        if not _:
            badge.name = badge_data['name']
            badge.badge_type = badge_data['badge_type']
            badge.rank = badge_data['rank']
            badge.link = badge_data['link']
            badge.description = badge_data['description']
            badge.save()
        
        # Create or update user-badge relationship
        StackUserBadge.objects.update_or_create(
            user=user,
            badge=badge,
            defaults={'award_count': badge_data.get('award_count', 1)}
        )
    
    return True

def update_collective_data(collective_id: str, api_key: str, access_token: str) -> bool:
    """
    Update collective data with complete information from Stack Exchange API
    
    Args:
        collective_id (str): The ID of the collective to update
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    collective_data = fetch_collective_data(collective_id, api_key, access_token)
    if not collective_data:
        return False
        
    collective, _ = StackCollective.objects.get_or_create(
        id=collective_id,
        defaults={
            'name': collective_data['name'],
            'description': collective_data['description'],
            'link': collective_data['link'],
            'slug': collective_data['slug'],
            'last_sync': int(timezone.now().timestamp())
        }
    )
    
    # Update collective if it already exists
    if not _:
        collective.name = collective_data['name']
        collective.description = collective_data['description']
        collective.link = collective_data['link']
        collective.slug = collective_data['slug']
        collective.last_sync = int(timezone.now().timestamp())
        collective.save()
    
    # Update collective tags
    for tag_name in collective_data.get('tags', []):
        tag, _ = StackTag.objects.get_or_create(name=tag_name)
        StackCollectiveTag.objects.get_or_create(
            collective=collective,
            tag=tag
        )
    
    # Update collective users
    for user_data in collective_data.get('users', []):
        user, _ = StackUser.objects.get_or_create(
            user_id=user_data['user_id'],
            defaults={
                'display_name': user_data.get('display_name'),
                'reputation': user_data.get('reputation', 0)
            }
        )
        
        StackCollectiveUser.objects.update_or_create(
            collective=collective,
            user=user,
            defaults={'role': user_data.get('role', 'member')}
        )
    
    return True

def populate_missing_data(api_key: str, access_token: str):
    """
    Populate missing data for users that need updating
    
    Args:
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
    """
    # Get users that need updating
    users_to_update = get_users_to_update()
    logger.info(f"Found {users_to_update.count()} users that need updating")
    
    # Update users
    for user in users_to_update:
        logger.info(f"Updating data for user {user.user_id}")
        update_user_data(user, api_key, access_token)
        time.sleep(1)  # Rate limiting
        
        # Only fetch badges if user data was successfully updated
        # if update_user_data(user, api_key, access_token):
        #     update_user_badges(user, api_key, access_token)
            
        #     # Update collectives if user has any
        #     if user.collectives:
        #         for collective_id in user.collectives:
        #             logger.info(f"Updating collective {collective_id} for user {user.user_id}")
        #             update_collective_data(collective_id, api_key, access_token)
        #             time.sleep(1)  # Rate limiting for collectives 