import requests
import time
import logging
import os
from django.utils import timezone
from django.db.models import Q
from stackoverflow.models import (
    StackUser, StackBadge, StackCollective, StackUserBadge,
    StackCollectiveUser, StackCollectiveTag, StackTag
)

logger = logging.getLogger(__name__)

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

def fetch_users_data(user_ids: list, api_key: str, access_token: str) -> list:
    """
    Fetch complete user data from Stack Exchange API in batch
    
    Args:
        user_ids (list): List of user IDs to fetch
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        list: List of user data dictionaries
    """
    # Stack Exchange API allows up to 100 IDs per request
    batch_size = 100
    all_users_data = []
    base_sleep_time = 2  # Start with 2 seconds
    max_sleep_time = 30  # Maximum sleep time of 30 seconds
    
    # Process user IDs in batches
    for i in range(0, len(user_ids), batch_size):
        batch_ids = user_ids[i:i + batch_size]
        ids_string = ';'.join(map(str, batch_ids))
        base_url = f"https://api.stackexchange.com/2.3/users/{ids_string}"
        
        logger.info(f"Fetching batch {i//batch_size + 1} with {len(batch_ids)} users")
        logger.info(f"First few IDs in batch: {batch_ids[:5]}")
        
        params = {
            'site': 'stackoverflow',
            'key': api_key,
            'access_token': access_token,
            'filter': '!T3Audpe81eZTLAf2z2'  # Filter for user data
        }
        
        while True:  # Retry loop with exponential backoff
            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get('items'):
                    all_users_data.extend(data['items'])
                    logger.info(f"Successfully fetched {len(data['items'])} users from API")
                else:
                    logger.warning(f"No data returned for batch {i//batch_size + 1}")
                
                # Check for rate limiting
                if 'quota_remaining' in data:
                    logger.info(f"Quota remaining: {data['quota_remaining']}")
                    if data['quota_remaining'] < 100:
                        logger.warning(f"Low quota remaining: {data['quota_remaining']}")
                        return all_users_data
                
                # Success - reset sleep time and break the retry loop
                base_sleep_time = 2
                break
                
            except requests.exceptions.RequestException as e:
                if hasattr(e, 'response') and e.response.status_code == 429:
                    # Too many requests - exponential backoff
                    logger.warning(f"Rate limited. Sleeping for {base_sleep_time} seconds...")
                    time.sleep(base_sleep_time)
                    base_sleep_time = min(base_sleep_time * 2, max_sleep_time)
                    continue
                elif hasattr(e, 'response') and e.response.status_code == 400:
                    # Bad request - might be invalid IDs
                    logger.error(f"Error fetching user data for batch {i//batch_size + 1}: {str(e)}")
                    logger.error(f"URL: {base_url}")
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response text: {e.response.text}")
                    break  # Don't retry on 400 errors
                else:
                    # Other errors
                    logger.error(f"Error fetching user data for batch {i//batch_size + 1}: {str(e)}")
                    break
        
        # Sleep between batches
        logger.info(f"Sleeping for {base_sleep_time} seconds before next batch...")
        time.sleep(base_sleep_time)
    
    return all_users_data

def update_users_data(users: list, api_key: str, access_token: str) -> bool:
    """
    Update multiple users' data with complete information from Stack Exchange API
    
    Args:
        users (list): List of StackUser objects to update
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        bool: True if any updates were successful, False otherwise
    """
    if not users:
        return False
        
    user_ids = [user.user_id for user in users]
    logger.info(f"Fetching data for {len(user_ids)} users")
    users_data = fetch_users_data(user_ids, api_key, access_token)
    
    if not users_data:
        logger.warning("No user data received from API")
        return False
    
    # Create a dictionary for quick lookup
    users_dict = {user.user_id: user for user in users}
    current_time = int(timezone.now().timestamp())
    updated_count = 0
    skipped_count = 0
    
    for user_data in users_data:
        user_id = user_data.get('user_id')
        if user_id not in users_dict:
            logger.warning(f"User ID {user_id} not found in local database")
            skipped_count += 1
            continue
            
        user = users_dict[user_id]
        
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
        user.time_mined = current_time
        
        user.save()
        updated_count += 1
    
    logger.info(f"Updated {updated_count} out of {len(users)} users")
    if skipped_count > 0:
        logger.warning(f"Skipped {skipped_count} users (not found in local database)")
    return updated_count > 0

def populate_missing_data(api_key: str, access_token: str):
    """
    Populate missing data for users that need updating
    
    Args:
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
    """
    # Get users that need updating
    users_to_update = get_users_to_update()
    total_users = users_to_update.count()
    logger.info(f"Found {total_users} users that need updating")
    
    if total_users == 0:
        return
    
    # Process users in batches of 100 (Stack Exchange API limit)
    batch_size = 100
    total_batches = (total_users + batch_size - 1) // batch_size
    logger.info(f"Will process {total_batches} batches of up to {batch_size} users each")
    
    for i in range(0, total_users, batch_size):
        batch = users_to_update[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} of {total_batches} ({len(batch)} users)")
        update_users_data(list(batch), api_key, access_token) 