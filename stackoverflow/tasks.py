# Em stackoverflow/tasks.py

from celery import shared_task
from django.conf import settings
from jobs.models import Task  # Importa o modelo Task

# Importa as suas funções de mineração originais
from .miner.question_fetcher import fetch_questions
from .miner.get_additional_data import populate_missing_data

# Em stackoverflow/tasks.py

@shared_task(bind=True)
def collect_questions_task(self, start_date: str, end_date: str, tags=None): # <-- MUDANÇA 1: Recebe 'tags'
    """
    Tarefa Celery que executa a coleta de perguntas e atualiza o status.
    """
    task_obj = None
    try:
        task_obj = Task.objects.get(task_id=self.request.id)
        
        # Passamos o task_obj e também as tags para a sua função de mineração
        fetch_questions(
            site='stackoverflow',
            start_date=start_date,
            end_date=end_date,
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj,
            tags=tags  # <-- MUDANÇA 2: Passa 'tags' para a função
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
    
@shared_task(bind=True)
def repopulate_users_task(self):
    """
    Tarefa Celery que executa o enriquecimento de dados e atualiza o status.
    """
    task_obj = None
    try:
        task_obj = Task.objects.get(task_id=self.request.id)
        
        populate_missing_data(
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj # <<-- O NOVO PARÂMETRO EM AÇÃO
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