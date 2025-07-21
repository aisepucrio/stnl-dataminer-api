# Em stackoverflow/tasks.py

from celery import shared_task
from django.conf import settings

# --- MUDANÇA PRINCIPAL AQUI ---
# Importamos a FUNÇÃO original que já funciona, não a classe que não existe mais.
from .functions.question_fetcher import fetch_questions

@shared_task
def collect_questions_task(start_date: str, end_date: str):
    """
    Esta é a nossa função de mineração transformada em uma "tarefa" do Celery.
    """
    print("▶️  Tarefa Celery 'collect_questions_task' iniciada...")

    # A lógica agora é chamar a função diretamente, como fazíamos no shell
    fetch_questions(
        site='stackoverflow',
        start_date=start_date,
        end_date=end_date,
        api_key=settings.STACK_API_KEY,
        access_token=settings.STACK_ACCESS_TOKEN
    )
    
    print("✅ Tarefa Celery 'collect_questions_task' finalizada.")
    return f"Coleta de {start_date} a {end_date} concluída pelo Celery."