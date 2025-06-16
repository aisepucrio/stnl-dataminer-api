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

def fetch_users_badges(user_ids: list, api_key: str, access_token: str) -> list:
    """
    Fetch all user badges with pagination and exponential backoff from Stack Exchange API

    Args:
        user_ids (list): List of user IDs to fetch badges for
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token

    Returns:
        list: List of user badges
    """
    ids_string = ';'.join(map(str, user_ids))
    base_url = f"https://api.stackexchange.com/2.3/users/{ids_string}/badges"

    all_badges = []
    page = 1
    base_sleep_time = 2
    max_sleep_time = 30

    while True:
        params = {
            'site': 'stackoverflow',
            'key': api_key,
            'access_token': access_token,
            'filter': '!nNPvSNZxzg',
            'page': page,
            'pagesize': 100
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            all_badges.extend(items)

            if 'quota_remaining' in data:
                logger.info(f"Quota remaining: {data['quota_remaining']}")
                if data['quota_remaining'] < 50:
                    logger.warning(f"Low quota remaining: {data['quota_remaining']}")
                    break

            if not data.get("has_more"):
                break

            page += 1
            base_sleep_time = 2  # reset if successful
            logger.info(f"Paginating to page {page} for badge data...")
            time.sleep(base_sleep_time)

        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 429:
                logger.warning(f"Rate limited on page {page}. Sleeping for {base_sleep_time} seconds...")
                time.sleep(base_sleep_time)
                base_sleep_time = min(base_sleep_time * 2, max_sleep_time)
                continue
            elif status_code == 400:
                logger.error(f"Bad request while fetching badges for user_ids {user_ids}: {str(e)}")
                break
            else:
                logger.error(f"Error fetching badges for user_ids {user_ids}: {str(e)}")
                break

    if not all_badges:
        logger.warning(f"No badges found for user_ids: {user_ids}")
    return all_badges


def update_badges_data(users: list, api_key: str, access_token: str) -> bool:
    """
    Update StackBadge and StackUserBadge based on badges fetched for users

    Args:
        users (list): List of StackUser objects
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token

    Returns:
        bool: True if any badge was inserted
    """
    if not users:
        return False

    user_ids = [user.user_id for user in users]
    logger.info(f"Fetching badges for {len(user_ids)} users")

    badge_data = fetch_users_badges(user_ids, api_key, access_token)
    if not badge_data:
        logger.warning("No badge data received from API")
        return False

    created_count = 0

    for item in badge_data:
        badge_name = item.get("name")
        badge_rank = item.get("rank")
        badge_type = item.get("badge_type")
        badge_link = item.get("link")
        badge_description = item.get("description")
        user_id = item.get("user", {}).get("user_id")

        badge_id = item.get("badge_id")
        if badge_id is None:
            continue  # Defensive programming

        badge_obj, _ = StackBadge.objects.get_or_create(
            badge_id=badge_id,
            defaults={
                "name": badge_name,
                "badge_type": badge_type,
                "rank": badge_rank,
                "link": badge_link,
                "description": badge_description or "",
            }
        )

        user = next((u for u in users if u.user_id == user_id), None)
        if user:
            _, created = StackUserBadge.objects.get_or_create(user=user, badge=badge_obj)
            if created:
                created_count += 1

    logger.info(f"Created {created_count} new StackUserBadge entries")
    return created_count > 0

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


def fetch_collectives_data(slugs: list, api_key: str, access_token: str) -> list:
    """
    Fetch collective data from Stack Exchange API with pagination and backoff

    Args:
        slugs (list): List of collective slugs to fetch
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token

    Returns:
        list: List of collective data dictionaries
    """
    batch_size = 100
    all_collectives_data = []
    base_sleep_time = 2
    max_sleep_time = 30

    for i in range(0, len(slugs), batch_size):
        batch_slugs = slugs[i:i + batch_size]
        slugs_string = ';'.join(batch_slugs)
        page = 1

        logger.info(f"Fetching collective batch {i // batch_size + 1} with {len(batch_slugs)} slugs")
        logger.info(f"First few slugs in batch: {batch_slugs[:5]}")

        while True:  # Pagination loop
            params = {
                'site': 'stackoverflow',
                'key': api_key,
                'access_token': access_token,
                'filter': '!nNPvSNVLQY',
                'page': page,
                'pagesize': 100
            }

            base_url = f"https://api.stackexchange.com/2.3/collectives/{slugs_string}"

            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()

                items = data.get('items', [])

                if items:
                    all_collectives_data.extend(items)
                    logger.info(f"Fetched {len(items)} collectives from page {page}")
                    for c in items:
                        StackCollective.objects.get_or_create(
                            slug=c.get("slug"),
                            defaults={
                                "name": c.get("name"),
                                "description": c.get("description", ""),
                                "link": c.get("link"),
                                "last_sync": int(timezone.now().timestamp())
                            }
                        )

                        #TODO: StackCollectiveTag for all tags in tags field. 
                else:
                    logger.warning(f"No data returned for collectives page {page}")

                if 'quota_remaining' in data:
                    logger.info(f"Quota remaining: {data['quota_remaining']}")
                    if data['quota_remaining'] < 100:
                        logger.warning(f"Low quota remaining: {data['quota_remaining']}")
                        return all_collectives_data

                if not data.get("has_more"):
                    break

                page += 1
                base_sleep_time = 2  # reset on success
                logger.info(f"Sleeping {base_sleep_time} before next page of collectives...")
                time.sleep(base_sleep_time)

            except requests.exceptions.RequestException as e:
                status_code = getattr(e.response, 'status_code', None)
                if status_code == 429:
                    logger.warning(f"Rate limited on collectives page {page}. Sleeping for {base_sleep_time} seconds...")
                    time.sleep(base_sleep_time)
                    base_sleep_time = min(base_sleep_time * 2, max_sleep_time)
                    continue
                elif status_code == 400:
                    logger.error(f"Bad request for collective slugs batch: {str(e)}")
                    break
                else:
                    logger.error(f"Error fetching collectives page {page}: {str(e)}")
                    break

    return all_collectives_data

def link_users_to_collectives(users: list, fallback_collectives_data: list = None):
    """
    For each user in the list, create StackCollectiveUser links
    based on their current user.collectives field.

    If a collective slug is not found in the DB, it will be created using the
    fallback_collectives_data (as returned from fetch_collectives_data).
    """
    from stackoverflow.models import StackCollective, StackCollectiveUser

    # Convert fallback_collectives_data (list) to dict {slug: collective_dict}
    if fallback_collectives_data and isinstance(fallback_collectives_data, list):
        fallback_collectives_data = {
            c["slug"]: c for c in fallback_collectives_data if "slug" in c
        }

    link_triples = []  # (user, slug, role)
    slugs = set()

    # Extract (user, slug, role) triples
    for user in users:
        for col in user.collectives or []:
            collective_obj = col.get("collective", {})
            slug = collective_obj.get("slug")
            role = col.get("role")
            if slug:
                link_triples.append((user, slug, role))
                slugs.add(slug)

    if not link_triples:
        return

    # Fetch all relevant collectives from DB
    slug_to_collective = {
        c.slug: c for c in StackCollective.objects.filter(slug__in=slugs)
    }

    created_count = 0
    for user, slug, role in link_triples:
        collective = slug_to_collective.get(slug)

        # If not found, try to create from fallback data
        if not collective and fallback_collectives_data:
            fallback = fallback_collectives_data.get(slug)
            if fallback:
                collective, _ = StackCollective.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name": fallback.get("name"),
                        "description": fallback.get("description", ""),
                        "link": fallback.get("link") or "",
                        "last_sync": int(timezone.now().timestamp())
                    }
                )
                slug_to_collective[slug] = collective  # Cache it
                logger.info(f"Created missing StackCollective: {slug}")
            else:
                logger.warning(f"Slug '{slug}' not found in fallback_collectives_data")

        if not collective:
            logger.warning(f"Could not link user {user.user_id} to missing slug '{slug}'")
            continue

        obj, created = StackCollectiveUser.objects.get_or_create(
            user=user,
            collective=collective,
            defaults={"role": role or "unknown"}
        )

        # If it already exists, update role if it's changed
        if not created and obj.role != (role or "unknown"):
            obj.role = role or "unknown"
            obj.save(update_fields=["role"])

        if created:
            created_count += 1

    logger.info(f"Created {created_count} StackCollectiveUser links for {len(users)} users.")

def sync_collective_tags(collectives_data: list):
    from stackoverflow.models import StackTag, StackCollective, StackCollectiveTag

    if not collectives_data:
        logger.warning("No collective data provided to sync_collective_tags")
        return

    # Gather all tag names and collective slugs
    tag_names = set()
    slug_to_tags = {}

    for col in collectives_data:
        slug = col.get("slug")
        tags = col.get("tags", [])
        if not slug or not tags:
            continue
        slug_to_tags[slug] = tags
        tag_names.update(tags)

    # Fetch/create StackTag objects
    tag_objs = {
        tag.name: tag for tag in StackTag.objects.filter(name__in=tag_names)
    }
    missing_tags = tag_names - tag_objs.keys()
    for tag_name in missing_tags:
        tag_obj = StackTag.objects.create(name=tag_name)
        tag_objs[tag_name] = tag_obj
        logger.info(f"Created missing StackTag: {tag_name}")

    # Fetch collectives
    collectives = {
        c.slug: c for c in StackCollective.objects.filter(slug__in=slug_to_tags.keys())
    }

    # Create missing StackCollectiveTag links
    created_count = 0
    for slug, tag_list in slug_to_tags.items():
        collective = collectives.get(slug)
        if not collective:
            logger.warning(f"Collective '{slug}' not found in DB. Skipping tag link.")
            continue

        for tag_name in tag_list:
            tag = tag_objs.get(tag_name)
            if not tag:
                logger.warning(f"Tag '{tag_name}' not found. Skipping.")
                continue

            _, created = StackCollectiveTag.objects.get_or_create(
                collective=collective,
                tag=tag
            )
            if created:
                created_count += 1

    logger.info(f"Created {created_count} StackCollectiveTag relationships.")


def fetch_users_data(user_ids: list, api_key: str, access_token: str) -> list:
    """
    Fetch complete user data from Stack Exchange API in batch with pagination and backoff

    Args:
        user_ids (list): List of user IDs to fetch
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token

    Returns:
        list: List of user data dictionaries
    """
    batch_size = 100
    all_users_data = []
    base_sleep_time = 2
    max_sleep_time = 30

    for i in range(0, len(user_ids), batch_size):
        batch_ids = user_ids[i:i + batch_size]
        ids_string = ';'.join(map(str, batch_ids))
        page = 1

        logger.info(f"Fetching batch {i // batch_size + 1} with {len(batch_ids)} users")
        logger.info(f"First few IDs in batch: {batch_ids[:5]}")
        
        while True:  # pagination loop
            params = {
                'site': 'stackoverflow',
                'key': api_key,
                'access_token': access_token,
                'filter': '!T3Audpe81eZTLAf2z2',
                'page': page,
                'pagesize': 100
            }

            base_url = f"https://api.stackexchange.com/2.3/users/{ids_string}"

            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()

                items = data.get('items', [])
                if items:
                    all_users_data.extend(items)
                    logger.info(f"Fetched {len(items)} users from page {page}")
                else:
                    logger.warning(f"No data returned for user page {page}")

                if 'quota_remaining' in data:
                    logger.info(f"Quota remaining: {data['quota_remaining']}")
                    if data['quota_remaining'] < 100:
                        logger.warning(f"Low quota remaining: {data['quota_remaining']}")
                        return all_users_data

                if not data.get("has_more"):
                    break

                page += 1
                base_sleep_time = 2  # reset on success
                logger.info(f"Sleeping {base_sleep_time} seconds before next user page...")
                time.sleep(base_sleep_time)

            except requests.exceptions.RequestException as e:
                status_code = getattr(e.response, 'status_code', None)
                if status_code == 429:
                    logger.warning(f"Rate limited on user page {page}. Sleeping for {base_sleep_time} seconds...")
                    time.sleep(base_sleep_time)
                    base_sleep_time = min(base_sleep_time * 2, max_sleep_time)
                    continue
                elif status_code == 400:
                    logger.error(f"Bad request fetching users: {str(e)}")
                    break
                else:
                    logger.error(f"Error fetching user page {page}: {str(e)}")
                    break

    return all_users_data


def update_users_data(users: list, api_key: str, access_token: str) -> set:
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
    unique_slugs = set()

    
    for user_data in users_data:
        user_id = user_data.get('user_id')
        if user_id not in users_dict:
            logger.warning(f"User ID {user_id} not found in local database")
            skipped_count += 1
            continue
            
        user = users_dict[user_id]

           # Collective slugs
        collectives = user_data.get('collectives', [])
        user.collectives = collectives
        for col in collectives:
            slug = col.get("collective", {}).get("slug")
            print("SLUGGGGGGGG:", slug)
            if slug:
                unique_slugs.add(slug)
        
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
    return unique_slugs

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

def main():
    """
    Main function to test badge, user, and collective fetching and population.
    Run this manually to test the badge + collective pipeline.
    """
    from django.conf import settings

    # Load credentials from env or settings
    api_key = os.getenv("STACK_API_KEY") or settings.STACK_API_KEY
    access_token = os.getenv("STACK_ACCESS_TOKEN") or settings.STACK_ACCESS_TOKEN

    if not api_key or not access_token:
        logger.error("API key or access token not provided.")
        return

    # Fetch a test slice of users
    # users = list(StackUser.objects.all()[7:20])
    users = list()
    user_2988 = StackUser.objects.filter(user_id=107301).first()
    if user_2988:
        users.append(user_2988)
    if not users:
        logger.warning("No users found in the database.")
        return

    logger.info(f"Updating data for {len(users)} users")
    unique_slugs = update_users_data(users, api_key, access_token)

    logger.info(f"Fetching badges for {len(users)} users")
    badge_updated = update_badges_data(users, api_key, access_token)

    if badge_updated:
        logger.info("Badge data successfully updated.")
    else:
        logger.info("No badge updates were made.")

    if unique_slugs:
        logger.info(f"Fetching collective data for {len(unique_slugs)} unique slugs")
        collectives = fetch_collectives_data(list(unique_slugs), api_key, access_token)
        logger.info(f"Fetched {len(collectives)} collectives")
        link_users_to_collectives(users, collectives)
        sync_collective_tags(collectives)
    else:
        logger.info("No collectives found to fetch")

