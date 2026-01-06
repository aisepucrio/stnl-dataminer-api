import requests
from datetime import datetime, timezone as dt_timezone, timedelta
import time
import logging
from stackoverflow.models import StackQuestion, StackUser, StackAnswer, StackTag, StackComment
from django.utils import timezone
from jobs.models import Task
from stackoverflow.utils import epoch_to_dt

logger = logging.getLogger(__name__)

def log_progress(message: str, level: str = "info", task_obj: Task = None):
    """
    Show feedback in the terminal and, if a task_obj is provided,
    persist the progress message to the database for the frontend.
    """
    emojis = {
        "info": "ℹ️", "success": "✅", "warning": "🟡", "error": "❌",
        "system": "⚙️", "fetch": "🔎", "save": "💾", "process": "🔄"
    }
    terminal_message = f"[StackOverflow] {emojis.get(level, '➡️ ')} {message}"
    print(terminal_message, flush=True)
    if task_obj:
        task_obj.operation = message
        task_obj.save(update_fields=["operation"])

def update_task_progress_date(task_obj: Task, completed_date: str) -> None:
    """
    Updates the task's date_last_update field to track scraping progress.

    Args:
        task_obj: Task object to update
        completed_date: Date string in YYYY-MM-DD format that was completely processed
    """
    if not task_obj:
        return
    try:
        # Convert string date to datetime (set to start of day UTC)
        completed_datetime = datetime.strptime(completed_date, "%Y-%m-%d")
        completed_datetime = completed_datetime.replace(tzinfo=dt_timezone.utc)

        # Update the task's progress date
        task_obj.date_last_update = completed_datetime
        task_obj.save(update_fields=["date_last_update"])

        print(f"[StackOverflow] 📅 Progress tracked: Completed scraping for {completed_date}", flush=True)
    except Exception as e:
        print(f"[StackOverflow] ⚠️ Warning: Could not update progress date: {str(e)}", flush=True)


def create_or_update_user(user_id, user_data):
    stack_user = None
    try:
        stack_user, created = StackUser.objects.get_or_create(
            user_id=user_id,
            defaults={
                'display_name': user_data.get('display_name'),
                'reputation': user_data.get('reputation', 0),
                'profile_image': user_data.get('profile_image'),
                'user_type': user_data.get('user_type'),
                'is_employee': user_data.get('is_employee', False),
                'creation_date': epoch_to_dt(user_data.get('creation_date')),
                'last_access_date': epoch_to_dt(user_data.get('last_access_date')),
                'last_modified_date': epoch_to_dt(user_data.get('last_modified_date')),
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
            stack_user.display_name = user_data.get('display_name', stack_user.display_name)
            stack_user.reputation = user_data.get('reputation', stack_user.reputation)
            stack_user.profile_image = user_data.get('profile_image', stack_user.profile_image)
            stack_user.user_type = user_data.get('user_type', stack_user.user_type)
            stack_user.is_employee = user_data.get('is_employee', stack_user.is_employee)
            stack_user.creation_date = epoch_to_dt(user_data.get('creation_date')) or stack_user.creation_date
            stack_user.last_access_date = epoch_to_dt(user_data.get('last_access_date')) or stack_user.last_access_date
            stack_user.last_modified_date = epoch_to_dt(user_data.get('last_modified_date')) or stack_user.last_modified_date
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
            'creation_date': epoch_to_dt(answer_data.get('creation_date')),
            'content_license': answer_data.get('content_license'),
            'last_activity_date': epoch_to_dt(answer_data.get('last_activity_date')),
            'owner': owner,
            'share_link': answer_data.get('share_link'),
            'body_markdown': answer_data.get('body_markdown'),
            'link': answer_data.get('link'),
            'title': answer_data.get('title'),
            'time_mined': timezone.now(),
        }
    )
    return answer

def create_comment(comment_data, parent, owner):
    """
    Create or fetch a StackComment and attach it to a question or answer,
    based on the 'parent' instance type.
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
            'creation_date': epoch_to_dt(comment_data.get('creation_date')),
            'content_license': comment_data.get('content_license'),
            'edited': comment_data.get('edited', False),
            'owner': owner,
            'body_markdown': comment_data.get('body_markdown'),
            'link': comment_data.get('link'),
            'time_mined': timezone.now(),
            'question': question_obj,
            'answer': answer_obj,
        }
    )
    return comment

def make_question_serializable(question_data, stack_user, question_tags):
    """Convert question data to a JSON-serializable structure for API/response use."""
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

def fetch_questions(
    site: str,
    start_date: str,
    end_date: str,
    api_key: str,
    access_token: str,
    page: int = 1,
    page_size: int = 100,
    task_obj=None,
    tags=None
):
    """
    Fetch questions from Stack Overflow with user-friendly feedback.
    """
    base_url = "https://api.stackexchange.com/2.3/questions"
    
    # convert start/end to date objects so we can iterate day-by-day
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    log_progress(f"Starting collection from {start_date} to {end_date}", "system", task_obj=task_obj)

    if tags:
        log_progress(f"Filtering by tags: {tags}", "info", task_obj=task_obj)

    questions = []
    total_processed = 0

    # iterate day-by-day and paginate inside each day to get a reliable per-day checkpoint
    current_day = start_dt
    while current_day <= end_dt:
        day_start_ts = int(datetime.combine(current_day, datetime.min.time()).timestamp())
        day_end_ts = int(datetime.combine(current_day, datetime.max.time()).timestamp())

        log_progress(f" Day {current_day.isoformat()}: fetching…", "fetch", task_obj=task_obj)

        params = {
            'site': site,
            'fromdate': day_start_ts,
            'todate': day_end_ts,
            'page': 1,
            'pagesize': min(page_size, 100),
            # iterate within the day from oldest -> newest so finishing means "all older or equal to this day"
            'order': 'asc',
            'sort': 'creation',
            'filter': '!2xWEp6FHz8hT56C1LBQjFx25D4Dzmr*3(8D4ngdB5g',
            'key': api_key,
            'access_token': access_token
        }
        if tags:
            params['tagged'] = tags

        has_more = True
        day_aborted = False
        # keep references to last response/data for day-level checks
        response = None
        data = None

        while has_more:
            try:
                log_progress(f"Fetching page {params['page']} for {current_day.isoformat()}...", "fetch", task_obj=task_obj)
                response = requests.get(base_url, params=params)
                log_progress(f"API responded with status {response.status_code}", "info", task_obj=task_obj)
                response.raise_for_status()
                data = response.json()

                if 'error_id' in data:
                    log_progress(f"API returned an error: {data.get('error_message', 'Unknown error')}", "error", task_obj=task_obj)
                    day_aborted = True
                    break

                items = data.get('items', [])
                if not items:
                    if params['page'] == 1:
                        log_progress(f" Day {current_day.isoformat()}: no questions.", "warning", task_obj=task_obj)
                    break

                log_progress(f"🔄 {len(items)} questions (page {params['page']}) — saving…", "process", task_obj=task_obj)

                # if this is the first page for the day, capture the day's total
                if params.get('page', 1) == 1:
                    day_total = data.get('total', 0)
                    # if the day has no items, bail out of day pagination
                    if day_total == 0:
                        log_progress(f" Day {current_day.isoformat()}: no questions.", "warning", task_obj=task_obj)
                        break
                    # per-day processed counter for logging
                    day_processed = 0

                for item in items:
                    # owner
                    owner_data = item.get('owner', {})
                    owner_id = owner_data.get('user_id')
                    stack_user = create_or_update_user(owner_id, owner_data) if owner_id else None
                    question_tags = item.get('tags', [])

                    q_payload = {
                        'question_id': item['question_id'],
                        'title': item.get('title'),
                        'body': item.get('body'),
                        'creation_date': epoch_to_dt(item.get('creation_date')),
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
                        'last_activity_date': epoch_to_dt(item.get('last_activity_date')),
                        'time_mined': timezone.now(),
                    }

                    stack_question, created = StackQuestion.objects.get_or_create(
                        question_id=q_payload['question_id'],
                        defaults=q_payload
                    )

                    # comments
                    for comment in item.get('comments', []) or []:
                        c_owner = comment.get('owner', {})
                        c_owner_id = c_owner.get('user_id')
                        c_user = create_or_update_user(c_owner_id, c_owner) if c_owner_id else None
                        create_comment(comment, stack_question, c_user)

                    # answers + answer comments
                    if item.get('is_answered'):
                        for answer in item.get('answers', []) or []:
                            a_owner = answer.get('owner', {})
                            a_owner_id = a_owner.get('user_id')
                            a_user = create_or_update_user(a_owner_id, a_owner) if a_owner_id else None
                            stack_answer = create_answer(answer, stack_question, a_user)

                            for a_comment in answer.get('comments', []) or []:
                                ac_owner = a_comment.get('owner', {})
                                ac_owner_id = ac_owner.get('user_id')
                                ac_user = create_or_update_user(ac_owner_id, ac_owner) if ac_owner_id else None
                                create_comment(a_comment, stack_answer, ac_user)

                    # tags
                    tag_objs = []
                    for tag_name in question_tags:
                        tag_obj, _ = StackTag.objects.get_or_create(name=tag_name)
                        tag_objs.append(tag_obj)
                    stack_question.tags.set(tag_objs)

                    # count only after persisted
                    total_processed += 1
                    day_processed += 1

                    # per-day processing logs: include the day for context and progress
                    title_preview = item.get('title', 'Untitled')[:60]
                    log_progress(f"[{current_day.isoformat()}] [{day_processed}/{day_total}] Processing: '{title_preview}...'", "save", task_obj=task_obj)

                    questions.append(make_question_serializable(q_payload, stack_user, question_tags))

                has_more = data.get('has_more', False)
                if has_more:
                    params['page'] += 1
                    log_progress("➡️ Moving to the next page…", "info", task_obj=task_obj)
                    time.sleep(1)

            except requests.exceptions.RequestException as e:
                log_progress(f"Connection error: {str(e)}", "error", task_obj=task_obj)
                # abort day without checkpoint
                day_aborted = True
                break
            except Exception as e:
                log_progress(f"An unexpected error occurred: {str(e)}", "error", task_obj=task_obj)
                day_aborted = True
                break

        # checkpoint the day only if we didn't abort (i.e., we finished all pages for that day)
        if not day_aborted:
            try:
                update_task_progress_date(task_obj, current_day.isoformat())
            except Exception:
                # already handled/logged inside update_task_progress_date
                pass

        current_day = current_day + timedelta(days=1)
    
    log_progress(f"Collection finished. {total_processed} questions processed in total.", "success", task_obj=task_obj)
    # update the task's last processed date (mark the period as completed)
    update_task_progress_date(task_obj, end_date)
    return questions
