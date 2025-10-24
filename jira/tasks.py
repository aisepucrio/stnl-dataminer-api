from celery import shared_task
from jira.miner import JiraMiner
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone as dj_tz

import traceback

from jobs.models import Task  # Imports the model that will save the progress


# Helper to reuse or create tasks
def _reuse_or_create_task(self, *, defaults, task_pk=None):
    if task_pk:
        update_data = {**defaults, "task_id": self.request.id}
        update_data.pop("date_init", None)
        updated = Task.objects.filter(pk=task_pk).update(**update_data)
        if updated:
            return Task.objects.get(pk=task_pk), False
    return Task.objects.get_or_create(task_id=self.request.id, defaults=defaults)


@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, issuetypes, start_date=None, end_date=None, task_pk=None):
    # Creates or updates the Task in the database (reutiliza quando task_pk fornecido)
    defaults = {
        "operation": f"Starting Jira issue collection: {project_key} on domain {jira_domain}",
        # Guard domain and project together for restart
        "repository": f"{jira_domain}/{project_key}",
        "status": "STARTED",
        "date_init": start_date,
        "date_end": end_date,
        "type": "jira_issues",
    }
    task_obj, _ = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

    try:
        print(f"Starting Jira issue collection: {project_key} on domain {jira_domain}", flush=True)

        # Passes the task_obj to the JiraMiner
        miner = JiraMiner(jira_domain, task_obj=task_obj)
        issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)

        print(f" Collection completed: {issues['total_issues']} issues collected.", flush=True)

        # Updates the task with success
        task_obj.status = "SUCCESS"
        task_obj.operation = f" Collection completed: {issues['total_issues']} issues collected."
        task_obj.result = issues
        task_obj.save(update_fields=["status", "operation", "result"])

        return {
            'status': 'success',
            'operation': 'collect_jira_issues',
            'repository': jira_domain,
            'data': issues
        }
    except JiraMiner.NoValidJiraTokenError as e:
        print(f"[JiraTask] No valid token: {e}", flush=True)
        task_obj.status = "FAILURE"
        task_obj.error_type = "NO_VALID_JIRA_TOKEN"
        task_obj.error = str(e)
        task_obj.token_validation_error = True
        task_obj.operation = str(e)
        task_obj.save(update_fields=["status", "error_type", "error", "token_validation_error", "operation"])
        return {
            'status': 'error',
            'code': 'NO_VALID_JIRA_TOKEN',
            'message': str(e),
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }
    except Exception as e:
        print(f" Unexpected error while collecting Jira issues: {e}\n{traceback.format_exc()}", flush=True)
        task_obj.status = "FAILURE"
        task_obj.error_type = "UNEXPECTED_EXCEPTION"
        task_obj.error = str(e)
        task_obj.result = {"traceback": traceback.format_exc()}
        task_obj.operation = f" Unexpected error: {str(e)}"
        task_obj.save(update_fields=["status", "error_type", "error", "result", "operation"])

        return {
            'status': 'error',
            'code': 'UNEXPECTED_EXCEPTION',
            'message': str(e),
            'traceback': traceback.format_exc(),
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }


@shared_task(bind=True, name="jira.restart_collection")
def restart_collection(self, task_pk: str):
    """Restart Jira issue collection from the last completed day."""
    task_obj = Task.objects.get(pk=task_pk)

    # Wait for repository
    repo = task_obj.repository or ""
    if "/" not in repo:
        # Without a project, we can't reliably restart
        self.update_state(state="FAILURE", meta={"error": "repository missing project key", "repository": repo})
        return {"status": "FAILURE", "error": "repository missing project key", "repository": repo}

    jira_domain, project_key = repo.split("/", 1)

    end_date = task_obj.date_end

    # Defines new start_date = (date_last_update + 1 day) or date_init
    base = task_obj.date_last_update or getattr(task_obj, "date_init", None)
    start_date = (base + timedelta(days=1)) if base else None
    if isinstance(start_date, datetime) and dj_tz.is_naive(start_date):
        start_date = dj_tz.make_aware(start_date, dj_tz.get_default_timezone())

    # Spawn a new task using the same Task (doesn't change date_init)
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
