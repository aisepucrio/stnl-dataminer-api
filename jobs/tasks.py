from celery import shared_task
from github.miner import GitHubMiner
from jira.miner import JiraMiner

@shared_task(bind=True)
def fetch_commits(self, repo_name, start_date=None, end_date=None):
    # Define a metadata no início
    self.update_state(meta={
        'operation': 'fetch_commits',
        'repository': repo_name
    })
    miner = GitHubMiner()
    commits = miner.get_commits(repo_name, start_date, end_date)
    return {
        'operation': 'fetch_commits',
        'repository': repo_name,
        'data': commits
    }

@shared_task(bind=True)
def fetch_issues(self, repo_name, start_date=None, end_date=None):
    self.update_state(meta={
        'operation': 'fetch_issues',
        'repository': repo_name
    })
    miner = GitHubMiner()
    issues = miner.get_issues(repo_name, start_date, end_date)
    return {
        'operation': 'fetch_issues',
        'repository': repo_name,
        'data': issues
    }

@shared_task(bind=True)
def fetch_pull_requests(self, repo_name, start_date=None, end_date=None):
    self.update_state(meta={
        'operation': 'fetch_pull_requests',
        'repository': repo_name
    })
    miner = GitHubMiner()
    pull_requests = miner.get_pull_requests(repo_name, start_date, end_date)
    return {
        'operation': 'fetch_pull_requests',
        'repository': repo_name,
        'data': pull_requests
    }

@shared_task(bind=True)
def fetch_branches(self, repo_name):
    self.update_state(meta={
        'operation': 'fetch_branches',
        'repository': repo_name
    })
    miner = GitHubMiner()
    branches = miner.get_branches(repo_name)
    return {
        'operation': 'fetch_branches',
        'repository': repo_name,
        'data': branches
    }

@shared_task(bind=True)
def collect_issue_types_task(self, jira_domain, jira_email, jira_api_token):
    self.update_state(meta={
        'operation': 'collect_issue_types',
        'repository': jira_domain
    })
    miner = JiraMiner(jira_domain, jira_email, jira_api_token)
    issue_types = miner.collect_issue_types()
    return {
        'operation': 'collect_issue_types',
        'repository': jira_domain,
        'data': issue_types
    }

@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    self.update_state(meta={
        'operation': 'collect_jira_issues',
        'repository': jira_domain
    })
    miner = JiraMiner(jira_domain, jira_email, jira_api_token)
    issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)
    return {
        'operation': 'collect_jira_issues',
        'repository': jira_domain,
        'data': issues
    }
