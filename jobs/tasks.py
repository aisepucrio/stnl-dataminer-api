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
def fetch_issues(self, repo_name, start_date=None, end_date=None, depth='basic'):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_issues',
            'repository': repo_name,
            'depth': depth
        }
    )
    try:
        miner = GitHubMiner()
        issues = miner.get_issues(repo_name, start_date, end_date, depth)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'depth': depth,
                'data': issues
            }
        )
        return {
            'operation': 'fetch_issues',
            'repository': repo_name,
            'depth': depth,
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
def fetch_pull_requests(self, repo_name, start_date=None, end_date=None, depth='basic'):
    """
    self - primeiro argumento automático do Celery devido ao bind=True
    repo_name - nome do repositório
    start_date - data inicial (opcional)
    end_date - data final (opcional)
    depth - profundidade da mineração (opcional, default='basic')
    """
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_pull_requests',
            'repository': repo_name,
            'depth': depth
        }
    )
    try:
        miner = GitHubMiner()
        pull_requests = miner.get_pull_requests(repo_name, start_date, end_date, depth)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'depth': depth,
                'data': pull_requests
            }
        )
        return {
            'status': 'success',
            'data': pull_requests
        }
    except Exception as e:
        return {
            'status': 'error',
            'error_type': type(e).__name__,
            'error_message': str(e)
        }

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
        raise

@shared_task(bind=True)
def fetch_metadata(self, repo_name):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_metadata',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()
        metadata = miner.get_repository_metadata(repo_name)
        
        # Serializar os dados antes de retornar
        metadata_dict = {
            'repository': metadata.repository,
            'stars_count': metadata.stars_count,
            'watchers_count': metadata.watchers_count,
            'used_by_count': metadata.used_by_count,
            'releases_count': metadata.releases_count,
            'forks_count': metadata.forks_count,
            'open_issues_count': metadata.open_issues_count,
            'languages': metadata.languages,
            'topics': metadata.topics,
            'created_at': metadata.created_at,
            'updated_at': metadata.updated_at,
            'description': metadata.description,
            'html_url': metadata.html_url,
            'contributors_count': metadata.contributors_count,
            'is_archived': metadata.is_archived,
            'is_template': metadata.is_template
        }
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_metadata',
                'repository': repo_name,
                'result': metadata_dict
            }
        )
        return metadata_dict
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_metadata',
                'repository': repo_name,
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise type(e)(str(e)).with_traceback(e.__traceback__) 