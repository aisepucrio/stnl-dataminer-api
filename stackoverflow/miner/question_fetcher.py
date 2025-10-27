import requests
from datetime import datetime
import time
import logging
from stackoverflow.models import StackQuestion, StackUser, StackAnswer, StackTag, StackComment
from django.utils import timezone
from django.db import transaction
from jobs.models import Task

logger = logging.getLogger(__name__)


def log_progress(message: str, level: str = "info", task_obj: Task = None):
    """
    Displays progress feedback in the terminal and, if a task_obj is provided,
    saves the progress to the database.
    """
    terminal_message = f"[StackOverflow] {level.upper()}: {message}"
    print(terminal_message, flush=True)

    if task_obj:
        task_obj.operation = message
        task_obj.save(update_fields=["operation"])


def create_or_update_user(user_id, user_data):
    """
    Creates or updates a StackUser entry in the database.
    """
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
                'time_mined': None
            }
        )
        if not created:
            # Update existing user fields if necessary
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
            stack_user.time_mined = None
            stack_user.save()
    except Exception as e:
        logger.error(f"Error processing StackUser with ID {user_data}: {e}")
    return stack_user


def create_answer(answer_data, question, owner):
    """
    Creates or retrieves a StackAnswer associated with a question.
    """
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
    """
    Creates or retrieves a StackComment associated with a question or answer.
    """
    question_obj = parent if isinstance(parent, StackQuestion) else None
    answer_obj = parent if isinstance(parent, StackAnswer) else None

    comment, _ = StackComment.objects.get_or_create(
        comment_id=comment_data.get('comment_id'),
        defaults={
            'post_type': comment_data.get('post_type'),
            'post_id': comment_data.get('post_id'),
            'body': comment_data.get('body'),
            'score': comment_data.get('score', 0),
            'creation_date': comment_data.get('creation_date'),
            'content_license': comment_data.get('content_license'),
            'edited': comment_data.get('edited', False),
            'owner': owner,
            'body_markdown': comment_data.get('body_markdown'),
            'link': comment_data.get('link'),
            'time_mined': int(time.time()),
            'question': question_obj,
            'answer': answer_obj,
        }
    )
    return comment


def make_question_serializable(question_data, stack_user, question_tags):
    """
    Converts question data into a JSON-serializable format.
    """
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


def fetch_questions(site: str, start_date: str, end_date: str, api_key: str, access_token: str,
                    page: int = 1, page_size: int = 100, task_obj=None, tags=None):
    """
    Fetches questions from Stack Overflow within a given date range.
    Provides detailed terminal feedback and stores results in the database.
    """
    base_url = "https://api.stackexchange.com/2.3/questions"

    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_timestamp = int(datetime.combine(start_dt.date(), datetime.min.time()).timestamp())
    end_timestamp = int(datetime.combine(end_dt.date(), datetime.max.time()).timestamp())

    log_progress(f"Starting collection from {start_date} to {end_date}", "system", task_obj=task_obj)

    params = {
        'site': site,
        'fromdate': start_timestamp,
        'todate': end_timestamp,
        'page': page,
        'pagesize': min(page_size, 100),
        'order': 'desc',
        'sort': 'creation',
        'filter': '!2xWEp6FHz8hT56C1LBQjFx25D4Dzmr*3(8D4ngdB5g',
        'key': api_key,
        'access_token': access_token
    }

    if tags:
        params['tagged'] = tags
        log_progress(f"Filtering by tags: {tags}", "info", task_obj=task_obj)

    questions = []
    total_questions_api = 0
    total_processed = 0
    has_more = True
    page = 1

    while has_more:
        try:
            params['page'] = page

            log_progress(f"Fetching page {params['page']}...", "fetch", task_obj=task_obj)
            response = requests.get(base_url, params=params)
            log_progress(f"API responded with status {response.status_code}", "info", task_obj=task_obj)

            response.raise_for_status()
            data = response.json()

            if 'error_id' in data:
                log_progress(f"API returned an error: {data.get('error_message', 'Unknown error')}", "error", task_obj=task_obj)
                break

            if page == 1:
                total_questions_api = data.get('total', 0)
                if total_questions_api == 0:
                    log_progress("No questions found for this period.", "warning", task_obj=task_obj)
                    return []
                log_progress(f"Total of {total_questions_api} questions found. Starting processing...", "info", task_obj=task_obj)

            items = data.get('items', [])
            if not items:
                if params['page'] == 1:
                    log_progress("No questions found for this period.", "warning", task_obj=task_obj)
                break

            log_progress(f"{len(items)} questions found. Saving to database...", "process", task_obj=task_obj)

            for item in items:
                total_processed += 1

                owner_data = item.get('owner', {})
                owner_id = owner_data.get('user_id')
                stack_user = create_or_update_user(owner_id, owner_data) if owner_id else None
                question_tags = item.get('tags', [])

                question_dict_for_saving = {
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
                    'content_license': item.get('content_license'),
                    'last_activity_date': item.get('last_activity_date'),
                    'time_mined': int(time.time()),
                }

                stack_question, _ = StackQuestion.objects.get_or_create(
                    question_id=question_dict_for_saving['question_id'],
                    defaults=question_dict_for_saving
                )

                serializable_question = make_question_serializable(question_dict_for_saving, stack_user, question_tags)
                questions.append(serializable_question)

                # Save comments
                for comment in item.get('comments', []):
                    comment_owner_data = comment.get('owner', {})
                    comment_owner = create_or_update_user(comment_owner_data.get('user_id'), comment_owner_data) if comment_owner_data.get('user_id') else None
                    create_comment(comment, stack_question, comment_owner)

                # Save answers
                if item.get('is_answered'):
                    for answer in item.get('answers', []):
                        answer_owner_data = answer.get('owner', {})
                        answer_owner = create_or_update_user(answer_owner_data.get('user_id'), answer_owner_data) if answer_owner_data.get('user_id') else None
                        stack_answer = create_answer(answer, stack_question, answer_owner)

                        for comment in answer.get('comments', []):
                            comment_owner_data = comment.get('owner', {})
                            comment_owner = create_or_update_user(comment_owner_data.get('user_id'), comment_owner_data) if comment_owner_data.get('user_id') else None
                            create_comment(comment, stack_answer, comment_owner)

                # Save tags
                tag_objs = [StackTag.objects.get_or_create(name=tag_name)[0] for tag_name in question_tags]
                stack_question.tags.set(tag_objs)

                title_preview = item.get('title', 'Untitled')[:60]
                log_progress(f"[{total_processed}/{total_questions_api}] Processing: '{title_preview}...'", "save", task_obj=task_obj)

            has_more = data.get('has_more', False)
            if has_more:
                page += 1
                log_progress("Moving to the next page...", "info", task_obj=task_obj)
                time.sleep(1)

        except requests.exceptions.RequestException as e:
            log_progress(f"Connection error: {str(e)}", "error", task_obj=task_obj)
            break
        except Exception as e:
            log_progress(f"An unexpected error occurred: {str(e)}", "error", task_obj=task_obj)
            break

    log_progress(f"Collection finished. Total of {total_processed} questions processed.", "success", task_obj=task_obj)
    return questions
