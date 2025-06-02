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
                return False, "Token inválido ou expirado"
            elif response.status_code == 403:
                return False, "Token sem permissões suficientes"
            elif response.status_code != 200:
                return False, f"Erro na API do GitHub: {response.status_code}"
            
            data = response.json()
            if 'rate' not in data:
                return False, "Token não tem acesso à API do GitHub"
            
            return True, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao validar token: {str(e)}")
            return False, f"Erro de conexão: {str(e)}"
        except Exception as e:
            logger.error(f"Erro inesperado ao validar token: {str(e)}")
            return False, f"Erro inesperado: {str(e)}"

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
            logger.info(f"Tarefa de falha criada para {operation} em {repository}")
        except Exception as e:
            logger.error(f"Erro ao criar tarefa de falha: {str(e)}") 