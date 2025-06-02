from celery import shared_task, group
from github.miner import GitHubMiner
from jira.miner import JiraMiner
from django.conf import settings
from datetime import datetime
from .models import Task
from celery.exceptions import Ignore

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
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
        miner = GitHubMiner()
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = token_result.get('error', 'Unknown error in token validation')
            error_type = 'TokenValidationError'
            
            task = Task.objects.get(task_id=self.request.id)
            task.status = 'FAILURE'
            task.error = error_msg
            task.error_type = error_type
            task.token_validation_error = True
            task.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_commits',
                    'repository': repo_name,
                    'commit_sha': commit_sha,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_commits',
                'repository': repo_name
            }
        
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
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = {
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha,
            'data': commits
        }
        task.save()
        
        return {
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha,
            'data': commits
        }
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'commit_sha': commit_sha,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg
            }
        )
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'FAILURE'
        task.error = error_msg
        task.error_type = error_type
        task.token_validation_error = error_type == 'TokenValidationError'
        task.save()
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_commits',
            'repository': repo_name
        }

@shared_task(bind=True)
def fetch_issues(self, repo_name, start_date=None, end_date=None, depth='basic'):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_issues',
            'repository': repo_name,
            'start_date': start_date,
            'end_date': end_date,
            'depth': depth
        }
    )

    try:
        miner = GitHubMiner()
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = token_result.get('error', 'Unknown error in token validation')
            error_type = 'TokenValidationError'
            
            task = Task.objects.get(task_id=self.request.id)
            task.status = 'FAILURE'
            task.error = error_msg
            task.error_type = error_type
            task.token_validation_error = True
            task.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_issues',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'token_validation_error': True
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_issues',
                'repository': repo_name,
                'token_validation_error': True
            }

        issues = miner.get_issues(repo_name, start_date, end_date, depth)
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = {
            'count': len(issues),
            'repository': repo_name,
            'start_date': start_date,
            'end_date': end_date,
            'depth': depth
        }
        task.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'count': len(issues),
                'start_date': start_date,
                'end_date': end_date,
                'depth': depth
            }
        )
        
        return {
            'status': 'SUCCESS',
            'count': len(issues),
            'repository': repo_name,
            'start_date': start_date,
            'end_date': end_date,
            'depth': depth
        }

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type
            }
        )
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'FAILURE'
        task.error = error_msg
        task.error_type = error_type
        task.save()
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_issues',
            'repository': repo_name
        }

@shared_task(bind=True)
def fetch_pull_requests(self, repo_name, start_date=None, end_date=None, depth='basic'):
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
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = f"Invalid token: {token_result.get('error', 'Unknown error')}"
            error_type = 'TokenValidationError'
            
            self.update_state(
                state='FAILURE',
                meta={
                    'status': 'FAILURE',
                    'error': error_msg,
                    'error_type': error_type,
                    'operation': 'fetch_pull_requests',
                    'repository': repo_name,
                    'token_validation_error': True
                }
            )
            
            task = Task.objects.get(task_id=self.request.id)
            task.status = 'FAILURE'
            task.error = error_msg
            task.error_type = error_type
            task.token_validation_error = True
            task.save()
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_pull_requests',
                'repository': repo_name
            }
        
        metadata = miner.get_repository_metadata(repo_name)
        
        pull_requests = miner.get_pull_requests(repo_name, start_date, end_date, depth)
        
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj

        prs_serializable = convert_datetime(pull_requests)
        
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'SUCCESS',
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'data': prs_serializable
            }
        )
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = {
            'status': 'SUCCESS',
            'operation': 'fetch_pull_requests',
            'repository': repo_name,
            'data': prs_serializable
        }
        task.save()
        
        return {
            'status': 'SUCCESS',
            'operation': 'fetch_pull_requests',
            'repository': repo_name,
            'data': prs_serializable
        }
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_pull_requests',
                'repository': repo_name
            }
        )
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'FAILURE'
        task.error = error_msg
        task.error_type = error_type
        task.save()
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_pull_requests',
            'repository': repo_name
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
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = token_result.get('error', 'Unknown error in token validation')
            error_type = 'TokenValidationError'
            
            task = Task.objects.get(task_id=self.request.id)
            task.status = 'FAILURE'
            task.error = error_msg
            task.error_type = error_type
            task.token_validation_error = True
            task.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_branches',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_branches',
                'repository': repo_name
            }
        
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
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = {
            'operation': 'fetch_branches',
            'repository': repo_name,
            'data': branches
        }
        task.save()
        
        return {
            'operation': 'fetch_branches',
            'repository': repo_name,
            'data': branches
        }
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_branches',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg
            }
        )
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'FAILURE'
        task.error = error_msg
        task.error_type = error_type
        task.token_validation_error = error_type == 'TokenValidationError'
        task.save()
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_branches',
            'repository': repo_name
        }

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
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = token_result.get('error', 'Unknown error in token validation')
            error_type = 'TokenValidationError'
            
            task = Task.objects.get(task_id=self.request.id)
            task.status = 'FAILURE'
            task.error = error_msg
            task.error_type = error_type
            task.token_validation_error = True
            task.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_metadata',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_metadata',
                'repository': repo_name
            }
            
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
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = metadata_dict
        task.save()
        
        return metadata_dict
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_metadata',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg
            }
        )
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'FAILURE'
        task.error = error_msg
        task.error_type = error_type
        task.token_validation_error = error_type == 'TokenValidationError'
        task.save()
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_metadata',
            'repository': repo_name
        }