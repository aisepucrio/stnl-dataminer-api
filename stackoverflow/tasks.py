# Em stackoverflow/tasks.py

from celery import shared_task
from django.conf import settings
from jobs.models import Task, Repository  # Importa Task e Repository

# Importa as suas funções de mineração originais
from .miner.question_fetcher import fetch_questions
from .miner.get_additional_data import populate_missing_data
@shared_task(bind=True)
def collect_questions_task(self, start_date: str, end_date: str, tags=None):
    """
    Tarefa Celery que executa a coleta de perguntas e atualiza o status.
    """
    task_obj = None
    try:
        repo, _ = Repository.objects.get_or_create(name="Stack Overflow", defaults={'platform': 'stackoverflow', 'owner': 'community'})
        operation_log = f"Iniciando coleta: {start_date} a {end_date}"
        if tags:
            operation_log += f" (Tags: {tags})"

        task_obj = Task.objects.create(
            task_id=self.request.id, 
            operation=operation_log, 
            repository=repo
        )
        
        fetch_questions(
            site='stackoverflow',
            start_date=start_date,
            end_date=end_date,
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj,
            tags=tags
        )
        
        task_obj.status = 'COMPLETED'
        task_obj.operation = "Coleta finalizada com sucesso."
        task_obj.save(update_fields=['status', 'operation'])
        
        return f"Coleta de {start_date} a {end_date} concluída."

    except Exception as e:
        if task_obj:
            task_obj.status = 'FAILED'
            task_obj.error = str(e)
            task_obj.save(update_fields=['status', 'error'])
        raise e
    
@shared_task(bind=True, ignore_result=True)
def repopulate_users_task(self, previous_task_result=None):
    """
    Tarefa Celery que executa o enriquecimento de dados e atualiza o status.
    """
    task_obj = None
    try:
        # Lógica para criar a Task, que também estava faltando
        repo, _ = Repository.objects.get_or_create(name="Stack Overflow", defaults={'platform': 'stackoverflow', 'owner': 'community'})
        task_obj = Task.objects.create(
            task_id=self.request.id, 
            operation="Iniciando enriquecimento de dados de usuários", 
            repository=repo
        )
        
        populate_missing_data(
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj
        )

        task_obj.status = 'COMPLETED'
        task_obj.operation = "Enriquecimento de dados finalizado com sucesso."
        task_obj.save(update_fields=['status', 'operation'])
        
        return "Repopulação de usuários concluída."

    except Exception as e:
        if task_obj:
            task_obj.status = 'FAILED'
            task_obj.error = str(e)
            task_obj.save(update_fields=['status', 'error'])
        raise e