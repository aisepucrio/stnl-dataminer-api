from celery import shared_task
from github.miner import GitHubMiner
from jira.miner import JiraMiner
from django.conf import settings
from datetime import datetime
import traceback

@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, issuetypes, start_date=None, end_date=None):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }
    )
    try:
        print(f"🔄 Starting Jira issue collection: {project_key} on domain {jira_domain}")
        miner = JiraMiner(jira_domain)
        issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)

        print(f'Printing issues: {issues}', flush=True)
        print(f"✅ Collection completed: {issues['total_issues']} issues collected.")

        return {
            'status': 'success',
            'operation': 'collect_jira_issues',
            'repository': jira_domain,
            'data': issues
        }

    except JiraMiner.NoValidJiraTokenError as e:
        print(f"[JiraTask] ❌ Sem token válido: {e}", flush=True)
        return {
            'status': 'error',
            'code': 'NO_VALID_JIRA_TOKEN',
            'message': str(e),
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }

    except Exception as e:
        print(f"❌ Erro inesperado ao coletar issues do Jira: {e}\n{traceback.format_exc()}")
        return {
            'status': 'error',
            'code': 'UNEXPECTED_EXCEPTION',
            'message': str(e),
            'traceback': traceback.format_exc(),
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }
