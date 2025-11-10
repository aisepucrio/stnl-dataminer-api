import traceback
import logging
import uuid
from celery import shared_task
from django.conf import settings
from jobs.models import Task

from .miner.question_fetcher import fetch_questions
from .miner.get_additional_data import populate_missing_data

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def collect_questions_task(self, start_date: str, end_date: str, tags=None, task_pk=None):
    """
    Celery task responsible for collecting Stack Overflow questions
    and updating the Task model accordingly. Handles token rotation and API failures gracefully.
    """
    task_obj = None

    try:
        operation_log = f"Starting question collection: {start_date} to {end_date}"
        if tags:
            operation_log += f" (Tags: {tags})"

        task_id = getattr(self.request, "id", None) or str(uuid.uuid4())

        if task_pk:
            task_obj = Task.objects.get(pk=task_pk)
            task_obj.operation = operation_log
            task_obj.status = "STARTED"
            task_obj.save(update_fields=["operation", "status"])
        else:
            task_obj = Task.objects.create(
                task_id=task_id,
                operation=operation_log,
                repository="Stack Overflow",
                status="STARTED",
                type="stack_questions",
                date_init=start_date,
                date_end=end_date,
            )

        logger.info(operation_log)

        result = fetch_questions(
            site="stackoverflow",
            start_date=start_date,
            end_date=end_date,
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj,
            tags=tags,
        )

        if not isinstance(result, (dict, list, str, int, float, type(None))):
            result = str(result)

        total = result.get("total", "N/A") if isinstance(result, dict) else "N/A"
        task_obj.status = "COMPLETED"
        task_obj.operation = f"Question collection successfully completed. ({total} questions)"
        task_obj.result = result
        task_obj.save(update_fields=["status", "operation", "result"])

        logger.info(f"[StackTask] Successfully collected questions: {result}")

        return {
            "status": "success",
            "operation": "collect_questions",
            "repository": "Stack Overflow",
            "result": result,
        }

    except Exception as e:
        message = str(e)
        error_type = "UNEXPECTED_EXCEPTION"
        code = "UNEXPECTED_EXCEPTION"

        if "token" in message.lower():
            error_type = "NO_VALID_STACK_TOKEN"
            code = "NO_VALID_STACK_TOKEN"
        elif "key" in message.lower() or "credential" in message.lower():
            error_type = "INVALID_API_CREDENTIALS"
            code = "INVALID_API_CREDENTIALS"

        logger.error(f"[StackTask] Error: {message}\n{traceback.format_exc()}")

        if task_obj:
            task_obj.status = "FAILURE"
            task_obj.error_type = error_type
            task_obj.error = message
            task_obj.operation = f"Error during collection: {message}"
            task_obj.save(update_fields=["status", "error_type", "error", "operation"])

        return {
            "status": "error",
            "code": code,
            "message": message,
            "traceback": traceback.format_exc(),
            "operation": "collect_questions",
            "repository": "Stack Overflow",
        }


@shared_task(bind=True, ignore_result=True)
def repopulate_users_task(self, previous_task_result=None):
    """
    Celery task that enriches user data and updates the Task model.
    """
    task_obj = None
    try:
        task_id = getattr(self.request, "id", None) or str(uuid.uuid4())

        task_obj = Task.objects.create(
            task_id=task_id,
            operation="Starting user data enrichment process",
            repository="Stack Overflow",
            status="STARTED",
            type="stack_users",
        )

        populate_missing_data(
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj,
        )

        task_obj.status = "COMPLETED"
        task_obj.operation = "User data enrichment successfully completed."
        task_obj.save(update_fields=["status", "operation"])

        logger.info("[StackTask] User data enrichment successfully completed.")
        return {"status": "success", "operation": "repopulate_users"}

    except Exception as e:
        logger.error(f"[StackTask] Unexpected error in user repopulation: {e}")
        if task_obj:
            task_obj.status = "FAILURE"
            task_obj.error = str(e)
            task_obj.save(update_fields=["status", "error"])
        return {"status": "error", "message": str(e)}
