from celery import shared_task, group
from github.miner import GitHubMiner
from jira.miner import JiraMiner
from django.conf import settings

@shared_task(bind=True)
def fetch_commits(self, repo_name, start_date=None, end_date=None, commit_sha=None):
    """
    Task para minerar commits de um repositório
    """
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha
        }
    )
    
    try:
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
        miner = GitHubMiner()
        
        metadata = miner.get_repository_metadata(repo_name)
        
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
                'error': str(e),
                'error_type': type(e).__name__
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
        
        metadata = miner.get_repository_metadata(repo_name)
        
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
    self - first argument automatically passed by Celery due to bind=True
    repo_name - repository name
    start_date - start date (optional)
    end_date - end date (optional)
    depth - mining depth (optional, default='basic')
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
        
        metadata = miner.get_repository_metadata(repo_name)
        
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
        
        metadata = miner.get_repository_metadata(repo_name)
        
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
        print(f"❌ Error collecting Jira issues: {e}\n{traceback.format_exc()}")
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

@shared_task(bind=True)
def collect_all(self, repo_name, start_date=None, end_date=None, depth='basic', collect_types=None):
    """
    Task para coletar dados específicos de um repositório simultaneamente
    """
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'collect_all',
            'repository': repo_name,
            'depth': depth,
            'collecting': collect_types
        }
    )
    
    try:
        tasks_to_run = []
        
        if 'commits' in collect_types:
            tasks_to_run.append(fetch_commits.s(repo_name, start_date, end_date))
        
        if 'issues' in collect_types:
            tasks_to_run.append(fetch_issues.s(repo_name, start_date, end_date, depth))
        
        if 'pull_requests' in collect_types:    
            tasks_to_run.append(fetch_pull_requests.s(repo_name, start_date, end_date, depth))
        
        if 'branches' in collect_types:
            tasks_to_run.append(fetch_branches.s(repo_name))
        
        if 'metadata' in collect_types:
            tasks_to_run.append(fetch_metadata.s(repo_name))
        
        tasks = group(tasks_to_run)
        
        result = tasks.apply_async()
        
        self.update_state(
            state='PROGRESS',
            meta={
                'operation': 'collect_all',
                'repository': repo_name,
                'depth': depth,
                'group_id': result.id,
                'collecting': collect_types
            }
        )
        
        return {
            'operation': 'collect_all',
            'repository': repo_name,
            'depth': depth,
            'group_id': result.id,
            'collecting': collect_types
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'collect_all',
                'repository': repo_name,
                'depth': depth,
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise