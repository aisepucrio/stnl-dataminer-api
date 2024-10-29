from celery import shared_task
from github.miner import GitHubMiner
from jira.miner import JiraMiner

@shared_task
def simple_task():
    return "Task completed successfully"

@shared_task
def fetch_commits(repo_name, start_date=None, end_date=None):
    miner = GitHubMiner()
    return miner.get_commits(repo_name, start_date, end_date)

@shared_task
def fetch_issues(repo_name, start_date=None, end_date=None):
    miner = GitHubMiner()
    return miner.get_issues(repo_name, start_date, end_date)

@shared_task
def fetch_pull_requests(repo_name, start_date=None, end_date=None):
    miner = GitHubMiner()
    return miner.get_pull_requests(repo_name, start_date, end_date)

@shared_task
def fetch_branches(repo_name):
    miner = GitHubMiner()
    return miner.get_branches(repo_name)

@shared_task(bind=True)
def collect_issue_types_task(self, jira_domain, jira_email, jira_api_token):
    miner = JiraMiner(jira_domain, jira_email, jira_api_token)
    return miner.collect_issue_types()

@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    miner = JiraMiner(jira_domain, jira_email, jira_api_token)
    return miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)
