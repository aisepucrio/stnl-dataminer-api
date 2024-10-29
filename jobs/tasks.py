from celery import shared_task
from jira.miner import JiraMiner

@shared_task(bind=True)
def collect_issue_types_task(self, jira_domain, jira_email, jira_api_token):
    miner = JiraMiner(jira_domain, jira_email, jira_api_token)
    return miner.collect_issue_types()

@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    miner = JiraMiner(jira_domain, jira_email, jira_api_token)
    return miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)
