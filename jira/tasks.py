from celery import shared_task
from github.miners import GitHubMiner
from jira.miner import JiraMiner
from django.conf import settings
from datetime import datetime
import traceback

from jobs.models import Task  # ⬅️ Imports the model that will save the progress


@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, issuetypes, start_date=None, end_date=None):
    # ⬇️ Creates or updates the Task in the database
    task_obj, _ = Task.objects.get_or_create(
        task_id=self.request.id,
        defaults={
            "operation": f"🔄 Starting Jira issue collection: {project_key} on domain {jira_domain}",
            "repository": jira_domain,
            "status": "STARTED",
        }
    )

    try:
        print(f"🔄 Starting Jira issue collection: {project_key} on domain {jira_domain}", flush=True)

        # ⬇️ Passes the task_obj to the JiraMiner
        miner = JiraMiner(jira_domain, task_obj=task_obj)
        issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)

        print(f"✅ Collection completed: {issues['total_issues']} issues collected.", flush=True)

        # ⬇️ Updates the task with success
        task_obj.status = "SUCCESS"
        task_obj.operation = f"✅ Collection completed: {issues['total_issues']} issues collected."
        task_obj.result = issues
        task_obj.save(update_fields=["status", "operation", "result"])

        return {
            'status': 'success',
            'operation': 'collect_jira_issues',
            'repository': jira_domain,
            'data': issues
        }

    except JiraMiner.NoValidJiraTokenError as e:
        print(f"[JiraTask] ❌ No valid token: {e}", flush=True)
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
        print(f"❌ Unexpected error while collecting Jira issues: {e}\n{traceback.format_exc()}", flush=True)
        task_obj.status = "FAILURE"
        task_obj.error_type = "UNEXPECTED_EXCEPTION"
        task_obj.error = str(e)
        task_obj.result = {"traceback": traceback.format_exc()}
        task_obj.operation = f"❌ Unexpected error: {str(e)}"
        task_obj.save(update_fields=["status", "error_type", "error", "result", "operation"])

        return {
            'status': 'error',
            'code': 'UNEXPECTED_EXCEPTION',
            'message': str(e),
            'traceback': traceback.format_exc(),
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }
