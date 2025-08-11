# --- TRECHO CORRIGIDO (Imports) ---
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from django.conf import settings  # Adicionado para buscar chaves da API de forma segura
# Importa a função que realmente faz o trabalho
from ..tasks import collect_questions_task, repopulate_users_task
# Mantemos este import para a outra função que não vamos mexer agora
from jobs.models import Task, Repository
# Mantemos os imports da documentação e de outros módulos
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter
import logging # Adicionado para registrar erros no terminal

# Cria um logger para este módulo
logger = logging.getLogger(__name__)

@extend_schema_view(
    collect_answers=extend_schema(
        summary="Collect Stack Overflow Answers",
        description="""
        Collect all answers from Stack Overflow within a date range and save them to the database.
        
        Notes:
        - Answers are saved to database in batches
        - Duplicate answers are updated if they exist
        - The API will automatically handle rate limiting
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "site": {"type": "string", "default": "stackoverflow"},
                    "start_date": {"type": "string", "format": "date", "description": "Start date in YYYY-MM-DD"},
                    "end_date": {"type": "string", "format": "date", "description": "End date in YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "total_answers": {"type": "integer"},
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "answer_id": {"type": "integer"},
                                "question_id": {"type": "integer"},
                                "body": {"type": "string"},
                                "creation_date": {"type": "string", "format": "date-time"},
                                "score": {"type": "integer"},
                                "is_accepted": {"type": "boolean"}
                            }
                        }
                    }
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            429: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        tags=["StackOverflow"]
    ),
    collect_questions=extend_schema(
        summary="Collect Stack Overflow Questions",
        description="""
        Collect all questions from Stack Overflow within a date range and save them to the database.
        
        Notes:
        - Questions are saved to database in batches
        - Duplicate questions are updated if they exist
        - The API will automatically handle rate limiting
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "site": {"type": "string", "default": "stackoverflow"},
                    "start_date": {"type": "string", "format": "date", "description": "Start date in YYYY-MM-DD"},
                    "end_date": {"type": "string", "format": "date", "description": "End date in YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "total_questions": {"type": "integer"},
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_id": {"type": "integer"},
                                "title": {"type": "string"},
                                "body": {"type": "string"},
                                "creation_date": {"type": "string", "format": "date-time"},
                                "score": {"type": "integer"},
                                "view_count": {"type": "integer"},
                                "answer_count": {"type": "integer"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "is_answered": {"type": "boolean"},
                                "accepted_answer_id": {"type": "integer", "nullable": True},
                                "owner": {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "integer"},
                                        "display_name": {"type": "string"},
                                        "reputation": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            429: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        tags=["StackOverflow"]
    ),
    re_populate_data=extend_schema(
        summary="Re-populate Stack Overflow User Data",
        description="""
        Re-populate user data including badges, collectives, and other user-related information.
        
        Notes:
        - Updates users that have never been mined or were mined more than a week ago
        - Processes users in batches of 100
        - Updates badges, collectives, and user information
        - The API will automatically handle rate limiting
        """,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {"type": "string"}
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        tags=["StackOverflow"]
    )
)
class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet for collecting Stack Overflow data.
    Provides endpoints for collecting questions and populating db with all necessary data.
    """
        
# --- SUBSTITUA SUA FUNÇÃO collect_questions POR ESTA ---

    @action(detail=False, methods=['post'], url_path='collect-questions')
    def collect_questions(self, request):
        try:
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')

            if not start_date or not end_date:
                return Response({'error': 'start_date e end_date são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
            
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
            
            # --- MUDANÇA AQUI ---
            # 1. Busca ou cria o objeto Repository
            repo, _ = Repository.objects.get_or_create(name="Stack Overflow")
            
            # 2. Inicia a tarefa do Celery
            task = collect_questions_task.delay(start_date=start_date, end_date=end_date)
            
            # 3. Cria o registro da Task, passando o objeto 'repo'
            Task.objects.create(
                task_id=task.id, 
                operation=f"Iniciando coleta de perguntas: {start_date} a {end_date}", 
                repository=repo # Passa o objeto, não o texto
            )
            
            return Response(
                {'task_id': task.id, 'status': 'Tarefa de coleta iniciada'}, 
                status=status.HTTP_202_ACCEPTED
            )

        except ValueError:
            return Response({'error': 'Formato de data inválido. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro ao enfileirar a tarefa 'collect_questions': {e}", exc_info=True)
            return Response({'error': f'Um erro inesperado ocorreu: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)      
        
    # --- SUBSTITUA SUA FUNÇÃO re_populate_data POR ESTA ---

    @action(detail=False, methods=['post'], url_path='re-populate-data')
    def re_populate_data(self, request):
        try:
            # --- MUDANÇA AQUI ---
            # 1. Busca ou cria o objeto Repository
            repo, _ = Repository.objects.get_or_create(name="Stack Overflow")
            
            # 2. Inicia a tarefa do Celery
            task = repopulate_users_task.delay()

            # 3. Cria o registro da Task, passando o objeto 'repo'
            Task.objects.create(
                task_id=task.id, 
                operation="Iniciando enriquecimento de dados de usuários", 
                repository=repo # Passa o objeto, não o texto
            )

            return Response(
                {'task_id': task.id, 'status': 'Tarefa de enriquecimento iniciada'}, 
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            logger.error(f"Erro ao enfileirar a tarefa 're_populate_data': {e}", exc_info=True)
            return Response({'error': f'Um erro inesperado ocorreu: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)