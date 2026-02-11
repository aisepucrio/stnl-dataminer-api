from celery import shared_task
from jira.miner import JiraMiner
from datetime import datetime, timedelta
from django.utils import timezone as dj_tz

import traceback
import uuid
from jobs.models import Task


def _reuse_or_create_task(self, *, defaults, task_pk=None):
    if task_pk:
        update_data = {**defaults, "task_id": getattr(getattr(self, "request", None), "id", None)}
        update_data.pop("date_init", None)
        updated = Task.objects.filter(pk=task_pk).update(**update_data)
        if updated:
            return Task.objects.get(pk=task_pk), False

    task_id = getattr(getattr(self, "request", None), "id", None) or str(uuid.uuid4())
    return Task.objects.get_or_create(task_id=task_id, defaults=defaults)


def _is_no_valid_jira_token_error(exc: Exception) -> bool:
    try:
        if isinstance(exc, JiraMiner.NoValidJiraTokenError):
            return True
    except TypeError:
        pass
    return exc.__class__.__name__ == "NoValidJiraTokenError"


@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, issuetypes, start_date=None, end_date=None, task_pk=None):
    if getattr(getattr(self, "request", None), "id", None):
        self.update_state(state="STARTED")

    repo_full = f"{jira_domain}/{project_key}"

    defaults = {
        "operation": f"Starting Jira issue collection: {project_key} on domain {jira_domain}",
        "repository": repo_full,
        "status": "STARTED",
        "date_init": start_date,
        "date_end": end_date,
        "type": "jira_issues",
    }
    task_obj, _ = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

    try:
        print(f"Starting Jira issue collection: {project_key} on domain {jira_domain}", flush=True)

        miner = JiraMiner(jira_domain, task_obj=task_obj)
        issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)

        result_payload = {
            **(issues or {}),
            "operation": "collect_jira_issues",
            "repository": repo_full,
        }

        task_obj.status = "SUCCESS"
        task_obj.operation = f"Collection completed: {result_payload.get('total_issues', 0)} issues collected."
        task_obj.result = result_payload
        task_obj.save(update_fields=["status", "operation", "result"])

        if getattr(getattr(self, "request", None), "id", None):
            self.update_state(state="SUCCESS", meta=result_payload)

        return result_payload

    except Exception as e:
        if _is_no_valid_jira_token_error(e):
            task_obj.status = "FAILURE"
            task_obj.error_type = "NO_VALID_JIRA_TOKEN"
            task_obj.error = str(e)
            task_obj.token_validation_error = True
            task_obj.operation = str(e)
            task_obj.result = {
                "status": "error",
                "operation": "collect_jira_issues",
                "repository": repo_full,
                "error": str(e),
                "code": "NO_VALID_JIRA_TOKEN",
            }
            task_obj.save(update_fields=["status", "error_type", "error", "token_validation_error", "operation", "result"])

            if getattr(getattr(self, "request", None), "id", None):
                self.update_state(state="FAILURE", meta=task_obj.result)

            return task_obj.result

        task_obj.status = "FAILURE"
        task_obj.error_type = "UNEXPECTED_EXCEPTION"
        task_obj.error = str(e)
        task_obj.result = {
            "status": "error",
            "operation": "collect_jira_issues",
            "repository": repo_full,
            "error": str(e),
            "code": "UNEXPECTED_EXCEPTION",
            "traceback": traceback.format_exc(),
        }
        task_obj.operation = f"Unexpected error: {str(e)}"
        task_obj.save(update_fields=["status", "error_type", "error", "result", "operation"])

        if getattr(getattr(self, "request", None), "id", None):
            self.update_state(state="FAILURE", meta=task_obj.result)

        return task_obj.result


@shared_task(bind=True, name="jira.restart_collection")
def restart_collection(self, task_pk: str):
    task_obj = Task.objects.get(pk=task_pk)

    repo = task_obj.repository or ""
    if "/" not in repo:
        self.update_state(state="FAILURE", meta={"error": "repository missing project key", "repository": repo})
        return {"status": "FAILURE", "error": "repository missing project key", "repository": repo}

    jira_domain, project_key = repo.split("/", 1)
    end_date = task_obj.date_end

    base = task_obj.date_last_update or getattr(task_obj, "date_init", None)
    start_date = (base + timedelta(days=1)) if base else None
    if isinstance(start_date, datetime) and dj_tz.is_naive(start_date):
        start_date = dj_tz.make_aware(start_date, dj_tz.get_default_timezone())

    new_task = collect_jira_issues_task.delay(
        jira_domain=jira_domain,
        project_key=project_key,
        issuetypes=[],
        start_date=start_date,
        end_date=end_date,
        task_pk=task_obj.pk,
    )

    self.update_state(state="SUCCESS", meta={"spawned_task_pk": task_obj.pk, "celery_id": new_task.id, "type": "jira_issues"})
    return {"status": "SUCCESS", "spawned_task_pk": task_obj.pk, "celery_id": new_task.id, "type": "jira_issues"}
