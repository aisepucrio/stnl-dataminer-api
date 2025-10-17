from celery import shared_task
from .miners import GitHubMiner
from jobs.models import Task
from datetime import datetime, timedelta
from django.utils import timezone as dj_tz

def format_date_for_json(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, str):
        return date_value
    if hasattr(date_value, 'isoformat'):
        return date_value.isoformat()
    return str(date_value)


# Helper to validate token
def _verify_token_or_fail(self, miner, task_obj, operation, repo_name, extra_meta_return=None):
    token_result = miner.verify_token()
    if token_result.get('valid'):
        return None  

    error_msg = token_result.get('error', 'Unknown error in token validation')
    error_type = 'TokenValidationError'

    task_obj.status = 'FAILURE'
    task_obj.error = error_msg
    task_obj.error_type = error_type
    task_obj.token_validation_error = True
    task_obj.save()

    extra_meta_return = extra_meta_return or {}
    failure_meta = {
        'operation': operation,
        'repository': repo_name,
        'error': error_msg,
        'error_type': error_type,
        'exc_type': error_type,
        'exc_message': error_msg,
        'exc_module': 'github.tasks',
        **extra_meta_return
    }

    self.update_state(state='FAILURE', meta=failure_meta)

    failure_return = {
        'status': 'FAILURE',
        'error': error_msg,
        'error_type': error_type,
        'operation': operation,
        'repository': repo_name,
        'token_validation_error': True,
        **{k: v for k, v in extra_meta_return.items() if k not in ('error', 'error_type')}
    }
    return failure_return

# Helper to reuse or create tasks
def _reuse_or_create_task(self, *, defaults, task_pk=None):
    if task_pk:
        update_data = {**defaults, "task_id": self.request.id}
        update_data.pop("date_init", None)
        updated = Task.objects.filter(pk=task_pk).update(**update_data)
        if updated:
            return Task.objects.get(pk=task_pk), False
    return Task.objects.get_or_create(task_id=self.request.id, defaults=defaults)


@shared_task(bind=True)
def fetch_commits(self, repo_name, start_date=None, end_date=None, commit_sha=None, task_pk=None):
    defaults = {
        "operation": f"🔄 Starting GitHub commit collection: {repo_name}",
        "repository": repo_name,
        "status": "STARTED",
        "error": None,
        "date_init": start_date,
        "date_end": end_date,
        "type": f"github_commits_{commit_sha}" if commit_sha else "github_commits",
    }
    task_obj, created = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

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

        token_failure = _verify_token_or_fail(
            self, miner, task_obj,
            operation='fetch_commits',
            repo_name=repo_name,               
            extra_meta_return={'commit_sha': commit_sha}
        )
        if token_failure:
            return token_failure


        commits = miner.get_commits(repo_name, start_date, end_date, commit_sha=commit_sha, task_obj=task_obj)

        task_obj.status = 'SUCCESS'
        task_obj.operation = f"Completed GitHub commit collection: {repo_name}"
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

        task_obj.operation = error_msg
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
def fetch_issues(self, repo_name, start_date=None, end_date=None, depth='basic', task_pk=None):
    defaults = {
        "operation": f"🔄 Starting GitHub issue collection: {repo_name}",
        "repository": repo_name,
        "status": "STARTED",
        "date_init": start_date,
        "date_end": end_date,
        "type": f"github_issues_{depth}",
    }
    task_obj, created = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_issues',
            'repository': repo_name,
            'error': None,
            'start_date': format_date_for_json(start_date),
            'end_date': format_date_for_json(end_date),
            'depth': depth
        }
    )

    try:
        miner = GitHubMiner()

        token_failure = _verify_token_or_fail(
            self, miner, task_obj,
            operation='fetch_issues',
            repo_name=repo_name,                    
            extra_meta_return={'depth': depth}
        )
        if token_failure:
            return token_failure

        miner.get_repository_metadata(repo_name)
        issues = miner.get_issues(repo_name, start_date, end_date, depth, task_obj)

        task_obj.status = 'SUCCESS'
        task_obj.operation = f"Completed GitHub issue collection: {repo_name}"
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

        task_obj.operation = error_msg
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
def fetch_pull_requests(self, repo_name, start_date=None, end_date=None, depth='basic', task_pk=None):
    defaults = {
        "operation": f"🔄 Starting GitHub pull request collection: {repo_name} ",
        "repository": repo_name,
        "status": "STARTED",
        "error": None,
        "date_init": start_date,
        "date_end": end_date,
        "type": f"github_pull_requests_{depth}",
    }
    task_obj, created = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

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

        token_failure = _verify_token_or_fail(
            self, miner, task_obj,
            operation='fetch_pull_requests',
            repo_name=repo_name,                    
            extra_meta_return={'depth': depth}
        )
        if token_failure:
            return token_failure

        miner.get_repository_metadata(repo_name)
        pull_requests = miner.get_pull_requests(repo_name, start_date, end_date, depth, task_obj)

        task_obj.status = 'SUCCESS'
        task_obj.operation = f"Completed GitHub pull request collection: {repo_name}"
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

        task_obj.operation = error_msg
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
def fetch_branches(self, repo_name, task_pk=None):
    defaults = {
        "operation": f"🔄 Starting GitHub branches collection: {repo_name}",
        "repository": repo_name,
        "error": None,
        "status": "STARTED",
        "type": "github_branches",
    }
    task_obj, created = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_branches',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()

        token_failure = _verify_token_or_fail(
            self, miner, task_obj,
            operation='fetch_branches',
            repo_name=repo_name,                    
            extra_meta_return=None
        )
        if token_failure:
            return token_failure

        miner.get_repository_metadata(repo_name)
        branches = miner.get_branches(repo_name)

        task_obj.status = 'SUCCESS'
        task_obj.operation = f"Completed GitHub branches collection: {repo_name}"
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

        task_obj.operation = error_msg
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
def fetch_metadata(self, repo_name, task_pk=None):
    defaults = {
        "operation": f"🔄 Starting GitHub metadata collection: {repo_name}",
        "repository": repo_name,
        "error": None,
        "status": "STARTED",
        "type": "github_metadata",
    }
    task_obj, created = _reuse_or_create_task(self, defaults=defaults, task_pk=task_pk)

    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_metadata',
            'repository': repo_name
        }
    )
    try:
        miner = GitHubMiner()


        token_failure = _verify_token_or_fail(
            self, miner, task_obj,
            operation='fetch_metadata',
            repo_name=repo_name,            
            extra_meta_return=None
        )
        if token_failure:
            return token_failure

        metadata = miner.get_repository_metadata(repo_name, task_obj)

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
            'github_created_at': format_date_for_json(metadata.github_created_at),
            'github_updated_at': format_date_for_json(metadata.github_updated_at),
            'is_archived': metadata.is_archived,
            'is_template': metadata.is_template,
            'used_by_count': metadata.used_by_count,
            'releases_count': metadata.releases_count,
            'time_mined': format_date_for_json(metadata.time_mined)
        }

        task_obj.status = 'SUCCESS'
        task_obj.operation = f"Completed GitHub metadata collection: {repo_name}"
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

        task_obj.operation = error_msg
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

@shared_task(bind=True, name="github.restart_collection")
def restart_collection(self, task_pk: str):
    task_obj = Task.objects.get(pk=task_pk)

    repo_name = task_obj.repository or ""
    collect_type = (task_obj.type or "").strip().lower()
    end_date = task_obj.date_end

    extra = None
    if "_" in collect_type:
        extra = collect_type.rsplit("_", 1)[1] or None

    base = task_obj.date_last_update or getattr(task_obj, "date_init", None)
    start_date = (base + timedelta(days=1)) if base else None
    if isinstance(start_date, datetime) and dj_tz.is_naive(start_date):
        start_date = dj_tz.make_aware(start_date, dj_tz.get_current_timezone())

    def _dispatch_issues():
        depth = extra
        return fetch_issues.apply_async(args=[repo_name, start_date, end_date, depth, task_pk]).id

    def _dispatch_prs():
        depth = extra
        return fetch_pull_requests.apply_async(args=[repo_name, start_date, end_date, depth, task_pk]).id

    def _dispatch_commits():
        commit_sha = None
        if extra != 'commits':
            commit_sha = extra
        return fetch_commits.apply_async(args=[repo_name, start_date, end_date, commit_sha, task_pk]).id

    def _dispatch_branches():
        return fetch_branches.apply_async(args=[repo_name, task_pk]).id

    def _dispatch_metadata():
        return fetch_metadata.apply_async(args=[repo_name, task_pk]).id

    if collect_type.startswith("github_issues"):
        new_id = _dispatch_issues()
    elif collect_type.startswith("github_pull_requests") or collect_type.startswith("github_pr"):
        new_id = _dispatch_prs()
    elif collect_type.startswith("github_commits"):
        new_id = _dispatch_commits()
    elif collect_type.startswith("github_branches"):
        new_id = _dispatch_branches()
    elif collect_type.startswith("github_metadata"):
        new_id = _dispatch_metadata()
    else:
        self.update_state(state="FAILURE", meta={"error": f"Tipo desconhecido: {collect_type}"})
        return {"status": "FAILURE", "error": f"Tipo desconhecido: {collect_type}"}

    self.update_state(state="SUCCESS", meta={"spawned_task_pk": new_id, "type": collect_type})
    return {"status": "SUCCESS", "spawned_task_pk": new_id, "type": collect_type}
