from celery import shared_task
from django.conf import settings
from jobs.models import Task
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
import traceback

from .miner.question_fetcher import fetch_questions


def _reuse_or_create_task(self, *, defaults, task_pk=None):
    if task_pk:
        update_data = {
            **defaults,
            "task_id": getattr(getattr(self, "request", None), "id", None),
        }
        update_data.pop("date_init", None)

        updated = Task.objects.filter(pk=task_pk).update(**update_data)
        if updated:
            return Task.objects.get(pk=task_pk), False

    task_id = getattr(getattr(self, "request", None), "id", None) or str(uuid.uuid4())
    return Task.objects.get_or_create(task_id=task_id, defaults=defaults)


@shared_task(bind=True)
def collect_questions_task(self, start_date: str, end_date: str, tags=None, filters=None, mode: str = "default", task_pk=None):
    task_obj = None

    try:
        operation_log = f"🔄 Starting collection: {start_date} to {end_date}"
        if tags:
            operation_log += f" (Tags: {tags})"

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

        result_payload = {
            "operation": "collect_questions",
            "repository": "stackoverflow",
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "filters": filters,
            "mode": mode,
            "status": "success",
        }

        task_obj.status = "COMPLETED"
        task_obj.operation = "✅ Collection completed successfully."
        task_obj.result = result_payload
        task_obj.save(update_fields=["status", "operation", "result"])

        return result_payload

    except Exception as e:
        msg = str(e)

        if "Invalid Stack token" in msg:
            code = "NO_VALID_STACK_TOKEN"
        elif "Invalid API key" in msg:
            code = "INVALID_API_CREDENTIALS"
        else:
            code = "UNEXPECTED_EXCEPTION"

        result_payload = {
            "operation": "collect_questions",
            "repository": "stackoverflow",
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "filters": filters,
            "mode": mode,
            "status": "error",
            "code": code,
            "message": msg,
        }

        if code == "UNEXPECTED_EXCEPTION":
            result_payload["traceback"] = traceback.format_exc()

        if task_obj:
            task_obj.status = "FAILURE"
            task_obj.error_type = code
            task_obj.error = msg
            task_obj.operation = msg
            task_obj.result = result_payload

            update_fields = ["status", "error_type", "error", "operation", "result"]

            if code in ("NO_VALID_STACK_TOKEN", "INVALID_API_CREDENTIALS"):
                task_obj.token_validation_error = True
                update_fields.append("token_validation_error")

            task_obj.save(update_fields=update_fields)

        return result_payload


@shared_task(bind=True, name="stackoverflow.restart_collection")
def restart_collection(self, task_pk: str):
    task_obj = Task.objects.get(pk=task_pk)
    collect_type = (task_obj.type or "").strip().lower()

    tags = getattr(task_obj, "tags", None)
    filters = getattr(task_obj, "filters", None)
    mode = getattr(task_obj, "mode", "default")

    if collect_type.startswith("stackoverflow_question_collection"):
        end_date = task_obj.date_end
        base = task_obj.date_last_update or getattr(task_obj, "date_init", None)
        start_date = (base + timedelta(days=1)) if base else None

        if isinstance(start_date, datetime) and timezone.is_naive(start_date):
            start_date = timezone.make_aware(
                start_date, timezone.get_current_timezone()
            )

        start_date_str = start_date.date().isoformat() if start_date else None
        end_date_str = end_date.date().isoformat() if end_date else None

        new_id = collect_questions_task.apply_async(
            args=[start_date_str, end_date_str, tags, filters, mode],
            kwargs={"task_pk": task_pk},
        ).id
    else:
        return {"status": "FAILURE", "error": f"Unknown task type: {collect_type}"}

    return {"status": "SUCCESS", "spawned_task_pk": new_id, "type": collect_type}
