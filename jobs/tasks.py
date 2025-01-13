from celery import shared_task
from github.miner import GitHubMiner
from jira.miner import JiraMiner

@shared_task(bind=True)
def fetch_commits(self, repo_name, start_date=None, end_date=None):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_commits',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()
        commits = miner.get_commits(repo_name, start_date, end_date)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'data': commits
            }
        )
        return {
            'operation': 'fetch_commits',
            'repository': repo_name,
            'data': commits
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'error': str(e)
            }
        )
        raise

@shared_task(bind=True)
def fetch_issues(self, repo_name, start_date=None, end_date=None):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_issues',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()
        issues = miner.get_issues(repo_name, start_date, end_date)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'data': issues
            }
        )
        return {
            'operation': 'fetch_issues',
            'repository': repo_name,
            'data': issues
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'error': str(e)
            }
        )
        raise

@shared_task(bind=True)
def fetch_pull_requests(self, repo_name, start_date=None, end_date=None):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_pull_requests',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()
        pull_requests = miner.get_pull_requests(repo_name, start_date, end_date)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'data': pull_requests
            }
        )
        return {
            'operation': 'fetch_pull_requests',
            'repository': repo_name,
            'data': pull_requests
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'error': str(e)
            }
        )
        raise

@shared_task(bind=True)
def fetch_branches(self, repo_name):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_branches',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()
        branches = miner.get_branches(repo_name)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_branches',
                'repository': repo_name,
                'data': branches
            }
        )
        return {
            'operation': 'fetch_branches',
            'repository': repo_name,
            'data': branches
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_branches',
                'repository': repo_name,
                'error': str(e)
            }
        )
        raise

@shared_task(bind=True)
def collect_issue_types_task(self, jira_domain, jira_email, jira_api_token):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'collect_issue_types',
            'repository': jira_domain
        }
    )
    try:
        miner = JiraMiner(jira_domain, jira_email, jira_api_token)
        issue_types = miner.collect_issue_types()
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'collect_issue_types',
                'repository': jira_domain,
                'data': issue_types
            }
        )
        return {
            'operation': 'collect_issue_types',
            'repository': jira_domain,
            'data': issue_types
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'collect_issue_types',
                'repository': jira_domain,
                'error': str(e)
            }
        )
        raise

@shared_task(bind=True)
def collect_jira_issues_task(self, jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }
    )
    try:
        miner = JiraMiner(jira_domain, jira_email, jira_api_token)
        issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'collect_jira_issues',
                'repository': jira_domain,
                'data': issues
            }
        )
        return {
            'operation': 'collect_jira_issues',
            'repository': jira_domain,
            'data': issues
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'collect_jira_issues',
                'repository': jira_domain,
                'error': str(e)
            }
        )
        raise e