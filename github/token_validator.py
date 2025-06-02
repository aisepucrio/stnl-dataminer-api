import requests
import logging
from django.utils import timezone
from jobs.models import Task

logger = logging.getLogger(__name__)

class TokenValidator:
    def __init__(self, token):
        self.token = token
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {token}'
        }

    def validate(self):

        try:
            response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
            
            if response.status_code == 401:
                return False, "Invalid or expired token"
            elif response.status_code == 403:
                return False, "Token does not have sufficient permissions"
            elif response.status_code != 200:
                return False, f"GitHub API error: {response.status_code}"
            
            data = response.json()
            if 'rate' not in data:
                return False, "Token does not have access to GitHub API"
            
            return True, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating token: {str(e)}")
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error validating token: {str(e)}")
            return False, f"Unexpected error: {str(e)}"

    @staticmethod
    def create_failed_task(operation, repository, error_message):
        try:
            Task.objects.create(
                task_id=None,  
                operation=operation,
                repository=repository,
                status='FAILURE',
                error=error_message,
                created_at=timezone.now()
            )
            logger.info(f"Failure task created for {operation} in {repository}")
        except Exception as e:
            logger.error(f"Error creating failure task: {str(e)}") 