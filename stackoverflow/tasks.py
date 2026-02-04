from celery import shared_task
from django.conf import settings
from jobs.models import Task
from django.utils import timezone
from datetime import datetime, timedelta

from .miner.question_fetcher import fetch_questions
from .miner.get_additional_data import populate_missing_data


# Helper to reuse or create tasks based on task_pk
def _reuse_or_create_task(self, *, defaults, task_pk=None):
    if task_pk:
        update_data = {**defaults, "task_id": self.request.id}
        # do not overwrite date_init on restarts
        update_data.pop("date_init", None)
        updated = Task.objects.filter(pk=task_pk).update(**update_data)
        if updated:
            return Task.objects.get(pk=task_pk), False
    return Task.objects.get_or_create(task_id=self.request.id, defaults=defaults)


@shared_task(bind=True)
def collect_questions_task(
    self,
    start_date: str,
    end_date: str,
    tags=None,
    filters=None,
    mode: str = "default",
    task_pk=None,
):
    """
    Celery task that collects Stack Overflow questions and updates task status.
    """
    task_obj = None
    try:
        operation_log = f"🔄 Starting collection: {start_date} to {end_date}"
        if tags:
            operation_log += f" (Tags: {tags})"
        if filters:
            operation_log += f" (Filters: {filters})"
        if mode:
            operation_log += f" (Mode: {mode})"

        defaults = {
            "operation": operation_log,
            "repository": "Stack Overflow",
            "status": "STARTED",
            "type": "stackoverflow_question_collection",
            "date_init": start_date,
            "date_end": end_date,
        }

        task_obj, _ = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

        fetch_questions(
            site="stackoverflow",
            start_date=start_date,
            end_date=end_date,
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj,
            tags=tags,
            filters=filters,
            mode=mode,
        )

        task_obj.status = "SUCCESS"
        task_obj.operation = "✅ Collection completed successfully."
        task_obj.save(update_fields=["status", "operation"])

        return f"Collection from {start_date} to {end_date} completed."

    except Exception as e:
        if task_obj:
            task_obj.status = "FAILURE"
            task_obj.error = str(e)
            task_obj.save(update_fields=["status", "error"])
        raise


@shared_task(bind=True, ignore_result=True)
def repopulate_users_task(self, previous_task_result=None):
    """
    Celery task that enriches user data and updates task status.
    """
    task_obj = None
    try:
        task_obj = Task.objects.create(
            task_id=self.request.id,
            operation="Starting user data enrichment",
            repository="Stack Overflow",
            status="STARTED",
            type="stackoverflow_user_repopulation",
        )

        populate_missing_data(
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj,
        )

        task_obj.status = "SUCCESS"
        task_obj.operation = "✅ User data enrichment finished successfully."
        task_obj.save(update_fields=["status", "operation"])

        return "User repopulation completed."

    except Exception as e:
        if task_obj:
            task_obj.status = "FAILURE"
            task_obj.error = str(e)
            task_obj.save(update_fields=["status", "error"])
        raise


@shared_task(bind=True, name="stackoverflow.restart_collection")
def restart_collection(self, task_pk: str):
    """
    Restart collection for a StackOverflow task from task.date_last_update + 1 day.
    """
    task_obj = Task.objects.get(pk=task_pk)
    collect_type = (task_obj.type or "").strip().lower()

    tags = getattr(task_obj, "tags", None)
    filters = getattr(task_obj, "filters", None)
    mode = getattr(task_obj, "mode", "default")

    if collect_type.startswith("stackoverflow_question_collection"):
        end_date = task_obj.date_end
        base = task_obj.date_last_update or getattr(task_obj, "date_init", None)
        start_date = (base + timedelta(days=1)) if base else None

        if isinstance(start_date, datetime):
            start_date_str = start_date.date().isoformat()
        elif hasattr(start_date, "isoformat"):
            start_date_str = start_date.isoformat()
        else:
            start_date_str = None

        if isinstance(end_date, datetime):
            end_date_str = end_date.date().isoformat()
        elif hasattr(end_date, "isoformat"):
            end_date_str = end_date.isoformat()
        else:
            end_date_str = None

        new_id = collect_questions_task.apply_async(
            args=[start_date_str, end_date_str, tags, filters, mode, task_pk]
        ).id

    else:
        self.update_state(
            state="FAILURE",
            meta={"error": f"Unknown task type: {collect_type}"}
        )
        return {"status": "FAILURE", "error": f"Unknown task type: {collect_type}"}

    self.update_state(
        state="SUCCESS",
        meta={"spawned_task_pk": new_id, "type": collect_type}
    )
    return {"status": "SUCCESS", "spawned_task_pk": new_id, "type": collect_type}
