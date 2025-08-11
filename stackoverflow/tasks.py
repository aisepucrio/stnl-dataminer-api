# Em stackoverflow/tasks.py

from celery import shared_task
from django.conf import settings
from jobs.models import Task  # Importa o modelo Task

# Importa as suas funções de mineração originais
from .miners.question_fetcher import fetch_questions
from .miners.data_populator import populate_missing_data

@shared_task(bind=True)
def collect_questions_task(self, start_date: str, end_date: str):
    """
    Tarefa Celery que executa a coleta de perguntas e atualiza o status.
    O 'bind=True' nos dá acesso ao 'self', que representa a própria tarefa.
    """
    task_obj = None
    try:
        # Usamos o ID da tarefa para buscar o objeto Task no banco de dados
        task_obj = Task.objects.get(task_id=self.request.id)
        
        # Passamos o task_obj para a sua função de mineração
        fetch_questions(
            site='stackoverflow',
            start_date=start_date,
            end_date=end_date,
            api_key=settings.STACK_API_KEY,
            access_token=settings.STACK_ACCESS_TOKEN,
            task_obj=task_obj  # <<-- O NOVO PARÂMETRO EM AÇÃO
        )
        
        # Se tudo correu bem, marcamos a tarefa como completa
        task_obj.status = 'COMPLETED'
        task_obj.operation = "Coleta finalizada com sucesso."
        task_obj.save(update_fields=['status', 'operation'])
        
        return f"Coleta de {start_date} a {end_date} concluída."

    except Exception as e:
        # Em caso de erro, atualizamos a tarefa com o status de falha
        if task_obj:
            task_obj.status = 'FAILED'
            task_obj.error = str(e)
            task_obj.save(update_fields=['status', 'error'])
        # O `raise` garante que o Celery também saiba que a tarefa falhou
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