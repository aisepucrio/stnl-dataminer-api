from celery import shared_task
from .miners import GitHubMiner
from jobs.models import Task
from datetime import datetime

def format_date_for_json(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, str):
        return date_value
    if hasattr(date_value, 'isoformat'):
        return date_value.isoformat()
    return str(date_value)

@shared_task(bind=True)
def fetch_commits(self, repo_name, start_date=None, end_date=None, commit_sha=None):
    task_obj, _ = Task.objects.get_or_create(
        task_id=self.request.id,
        defaults={
            "operation": f"🔄 Starting GitHub commit collection: {repo_name}",
            "repository": repo_name,
            "status": "STARTED",
        }
    )

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_commits',
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
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
            
            task_obj.status = 'FAILURE'
            task_obj.error = error_msg
            task_obj.error_type = error_type
            task_obj.token_validation_error = True
            task_obj.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_commits',
                    'repository': repo_name,
                    'commit_sha': commit_sha,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg,
                    'exc_module': 'github.tasks'
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
        
        commits = miner.get_commits(repo_name, start_date, end_date, commit_sha=commit_sha, task_obj=task_obj)
        
        task_obj.status = 'SUCCESS'
        task_obj.result = {
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'data': commits
        }
        task_obj.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'commit_sha': commit_sha,
                'start_date': format_date_for_json(start_date),
                'end_date': format_date_for_json(end_date),
                'data': commits
            }
        )
        
        return {
            'operation': 'fetch_commits',
            'repository': repo_name,
            'commit_sha': commit_sha,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'data': commits
        }
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        task_obj.status = 'FAILURE'
        task_obj.error = error_msg
        task_obj.error_type = error_type
        task_obj.save()
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_commits',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg,
                'exc_module': e.__class__.__module__
            }
        )
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_commits',
            'repository': repo_name
        }

@shared_task(bind=True)
def fetch_issues(self, repo_name, start_date=None, end_date=None, depth='basic'):
    task_obj, _ = Task.objects.get_or_create(
        task_id=self.request.id,
        defaults={
            "operation": f"🔄 Starting GitHub issue collection: {repo_name}",
            "repository": repo_name,
            "status": "STARTED",
        }
    )

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_issues',
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }
    )

    try:
        miner = GitHubMiner()
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = token_result.get('error', 'Unknown error in token validation')
            error_type = 'TokenValidationError'
            
            task_obj.status = 'FAILURE'
            task_obj.error = error_msg
            task_obj.error_type = error_type
            task_obj.token_validation_error = True
            task_obj.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_issues',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg,
                    'exc_module': 'github.tasks'
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

        miner.get_repository_metadata(repo_name)
        issues = miner.get_issues(repo_name, start_date, end_date, depth, task_obj)
        
        task_obj.status = 'SUCCESS'
        task_obj.result = {
            'count': len(issues),
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }
        task_obj.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'count': len(issues),
                'start_date': format_date_for_json(start_date),
                'end_date': format_date_for_json(end_date),
                'depth': depth
            }
        )
        
        return {
            'status': 'SUCCESS',
            'count': len(issues),
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        task_obj.status = 'FAILURE'
        task_obj.error = error_msg
        task_obj.error_type = error_type
        task_obj.save()
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_issues',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg,
                'exc_module': e.__class__.__module__
            }
        )
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_issues',
            'repository': repo_name
        }

@shared_task(bind=True)
def fetch_pull_requests(self, repo_name, start_date=None, end_date=None, depth='basic'):
    task_obj, _ = Task.objects.get_or_create(
        task_id=self.request.id,
        defaults={
            "operation": f"🔄 Starting GitHub pull request collection: {repo_name}",
            "repository": repo_name,
            "status": "STARTED",
        }
    )

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_pull_requests',
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }
    )
    try:
        miner = GitHubMiner()
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = f"Invalid token: {token_result.get('error', 'Unknown error')}"
            error_type = 'TokenValidationError'
            
            task_obj.status = 'FAILURE'
            task_obj.error = error_msg
            task_obj.error_type = error_type
            task_obj.token_validation_error = True
            task_obj.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_pull_requests',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg,
                    'exc_module': 'github.tasks'
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'token_validation_error': True
            }

        miner.get_repository_metadata(repo_name)
        pull_requests = miner.get_pull_requests(repo_name, start_date, end_date, depth, task_obj)
        
        task_obj.status = 'SUCCESS'
        task_obj.result = {
            'count': len(pull_requests),
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }
        task_obj.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'count': len(pull_requests),
                'start_date': format_date_for_json(start_date),
                'end_date': format_date_for_json(end_date),
                'depth': depth
            }
        )
        
        return {
            'status': 'SUCCESS',
            'count': len(pull_requests),
            'repository': repo_name,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        task_obj.status = 'FAILURE'
        task_obj.error = error_msg
        task_obj.error_type = error_type
        task_obj.save()
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_pull_requests',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg,
                'exc_module': e.__class__.__module__
            }
        )
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_pull_requests',
            'repository': repo_name
        }

@shared_task(bind=True)
def fetch_branches(self, repo_name):
    task_obj, _ = Task.objects.get_or_create(
        task_id=self.request.id,
        defaults={
            "operation": f"🔄 Starting GitHub branches collection: {repo_name}",
            "repository": repo_name,
            "status": "STARTED",
        }
    )

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
            error_msg = f"Invalid token: {token_result.get('error', 'Unknown error')}"
            error_type = 'TokenValidationError'
            
            task_obj.status = 'FAILURE'
            task_obj.error = error_msg
            task_obj.error_type = error_type
            task_obj.token_validation_error = True
            task_obj.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_branches',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg,
                    'exc_module': 'github.tasks'
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_branches',
                'repository': repo_name,
                'token_validation_error': True
            }

        miner.get_repository_metadata(repo_name)
        branches = miner.get_branches(repo_name)
        
        task_obj.status = 'SUCCESS'
        task_obj.result = {
            'count': len(branches),
            'repository': repo_name
        }
        task_obj.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_branches',
                'repository': repo_name,
                'count': len(branches)
            }
        )
        
        return {
            'status': 'SUCCESS',
            'count': len(branches),
            'repository': repo_name
        }

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        task_obj.status = 'FAILURE'
        task_obj.error = error_msg
        task_obj.error_type = error_type
        task_obj.save()
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_branches',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg,
                'exc_module': e.__class__.__module__
            }
        )
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_branches',
            'repository': repo_name
        }

@shared_task(bind=True)
def fetch_metadata(self, repo_name):
    task_obj, _ = Task.objects.get_or_create(
        task_id=self.request.id,
        defaults={
            "operation": f"🔄 Starting GitHub metadata collection: {repo_name}",
            "repository": repo_name,
            "status": "STARTED",
        }
    )

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
            error_msg = f"Invalid token: {token_result.get('error', 'Unknown error')}"
            error_type = 'TokenValidationError'
            
            task_obj.status = 'FAILURE'
            task_obj.error = error_msg
            task_obj.error_type = error_type
            task_obj.token_validation_error = True
            task_obj.save()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'operation': 'fetch_metadata',
                    'repository': repo_name,
                    'error': error_msg,
                    'error_type': error_type,
                    'exc_type': error_type,
                    'exc_message': error_msg,
                    'exc_module': 'github.tasks'
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_metadata',
                'repository': repo_name,
                'token_validation_error': True
            }

        metadata = miner.get_repository_metadata(repo_name)
        
        metadata_dict = {
            'repository': metadata.repository,
            'owner': metadata.owner,
            'organization': metadata.organization,
            'stars_count': metadata.stars_count,
            'watchers_count': metadata.watchers_count,
            'forks_count': metadata.forks_count,
            'open_issues_count': metadata.open_issues_count,
            'default_branch': metadata.default_branch,
            'description': metadata.description,
            'html_url': metadata.html_url,
            'contributors_count': metadata.contributors_count,
            'topics': metadata.topics,
            'languages': metadata.languages,
            'readme': metadata.readme,
            'labels_count': metadata.labels_count,
            'created_at': format_date_for_json(metadata.created_at),
            'updated_at': format_date_for_json(metadata.updated_at),
            'is_archived': metadata.is_archived,
            'is_template': metadata.is_template,
            'used_by_count': metadata.used_by_count,
            'releases_count': metadata.releases_count,
            'time_mined': format_date_for_json(metadata.time_mined)
        }
        
        task_obj.status = 'SUCCESS'
        task_obj.result = {
            'repository': repo_name,
            'metadata': metadata_dict
        }
        task_obj.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_metadata',
                'repository': repo_name,
                'metadata': metadata_dict
            }
        )
        
        return {
            'status': 'SUCCESS',
            'repository': repo_name,
            'metadata': metadata_dict
        }

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        task_obj.status = 'FAILURE'
        task_obj.error = error_msg
        task_obj.error_type = error_type
        task_obj.save()
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_metadata',
                'repository': repo_name,
                'error': error_msg,
                'error_type': error_type,
                'exc_type': error_type,
                'exc_message': error_msg,
                'exc_module': e.__class__.__module__
            }
        )
        
        return {
            'status': 'FAILURE',
            'error': error_msg,
            'error_type': error_type,
            'operation': 'fetch_metadata',
            'repository': repo_name
        } 