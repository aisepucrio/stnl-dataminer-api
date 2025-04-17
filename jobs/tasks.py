from celery import shared_task
from github.miner import GitHubMiner
from jira.miner import JiraMiner
from django.conf import settings

@shared_task(bind=True)
def fetch_commits(self, repo_name, start_date=None, end_date=None, commit_sha=None):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha
        }
    )
    try:
        miner = GitHubMiner()
        commits = miner.get_commits(repo_name, start_date, end_date, commit_sha=commit_sha)
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'commit_sha': commit_sha,
                'data': commits
            }
        )
        return {
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha,
            'data': commits
        }
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'commit_sha': commit_sha,
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
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise type(e)(str(e)).with_traceback(e.__traceback__)

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
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise type(e)(str(e)).with_traceback(e.__traceback__)

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
def collect_jira_issues_task(self, jira_domain, project_key, issuetypes, start_date=None, end_date=None):
    jira_email = settings.JIRA_EMAIL
    jira_api_token = settings.JIRA_API_TOKEN

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'collect_jira_issues',
            'repository': jira_domain
        }
    )
    try:
        print(f"🔄 Iniciando coleta de issues do Jira: {project_key} no domínio {jira_domain}")
        
        miner = JiraMiner(jira_domain)

        issues = miner.collect_jira_issues(project_key, issuetypes, start_date, end_date)

        print(f'Printing issues: {issues}', flush=True)

        print(f"✅ Coleta concluída: {issues['total_issues']} issues coletadas.")

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
        print(f"❌ Erro ao coletar issues do Jira: {e}\n{traceback.format_exc()}")
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