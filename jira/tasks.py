from celery import shared_task
from .miner import JiraMiner
from jobs.models import Task
from datetime import datetime

@shared_task(bind=True)
def fetch_issues(self, project_key, start_date=None, end_date=None, depth='basic'):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_issues',
            'project': project_key,
            'start_date': start_date,
            'end_date': end_date,
            'depth': depth
        }
    )
    try:
        miner = JiraMiner()
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = f"Invalid token: {token_result.get('error', 'Unknown error')}"
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
                    'project': project_key,
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
                'project': project_key,
                'token_validation_error': True
            }

        issues = miner.get_issues(project_key, start_date, end_date, depth)
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = {
            'count': len(issues),
            'project': project_key,
            'start_date': start_date,
            'end_date': end_date,
            'depth': depth
        }
        task.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_issues',
                'project': project_key,
                'count': len(issues),
                'start_date': start_date,
                'end_date': end_date,
                'depth': depth
            }
        )
        
        return {
            'status': 'SUCCESS',
            'count': len(issues),
            'project': project_key,
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
                'project': project_key,
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
            'project': project_key
        }

@shared_task(bind=True)
def fetch_metadata(self, project_key):
    self.update_state(
        state='STARTED',
        meta={
            'operation': 'fetch_metadata',
            'project': project_key
        }
    )
    try:
        miner = JiraMiner()
        
        token_result = miner.verify_token()
        if not token_result['valid']:
            error_msg = f"Invalid token: {token_result.get('error', 'Unknown error')}"
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
                    'project': project_key,
                    'error': error_msg,
                    'error_type': error_type,
                    'token_validation_error': True
                }
            )
            
            return {
                'status': 'FAILURE',
                'error': error_msg,
                'error_type': error_type,
                'operation': 'fetch_metadata',
                'project': project_key,
                'token_validation_error': True
            }

        metadata = miner.get_project_metadata(project_key)
        
        task = Task.objects.get(task_id=self.request.id)
        task.status = 'SUCCESS'
        task.result = {
            'project': project_key,
            'metadata': metadata
        }
        task.save()
        
        self.update_state(
            state='SUCCESS',
            meta={
                'operation': 'fetch_metadata',
                'project': project_key,
                'metadata': metadata
            }
        )
        
        return {
            'status': 'SUCCESS',
            'project': project_key,
            'metadata': metadata
        }

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        self.update_state(
            state='FAILURE',
            meta={
                'operation': 'fetch_metadata',
                'project': project_key,
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
            'operation': 'fetch_metadata',
            'project': project_key
        } 