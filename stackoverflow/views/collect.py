# Em stackoverflow/views/collect.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from datetime import datetime
import logging
from celery import chain

# Imports dos nossos módulos
from ..tasks import collect_questions_task, repopulate_users_task
from jobs.models import Task, Repository
from drf_spectacular.utils import extend_schema # Para documentação da API

# O "Cardápio" de operações agora vive aqui dentro
OPERATIONS = {
    'collect_questions': {
        'name': 'Coletar Novas Perguntas',
        'dependencies': []
    },
    'repopulate_users': {
        'name': 'Enriquecer Dados de Usuários',
        'dependencies': ['collect_questions']
    }
}

logger = logging.getLogger(__name__)

class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet para iniciar e gerenciar trabalhos de coleta de dados do Stack Overflow.
    """
    
    @extend_schema(
        summary="Inicia um Trabalho de Mineração do Stack Overflow",
        description="""
        Inicia um novo trabalho de mineração assíncrono com base em uma lista de operações.
        Este é o endpoint principal para todas as tarefas de coleta e enriquecimento de dados.
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de operações a serem executadas (ex: ['collect_questions', 'repopulate_users'])"
                    },
                    "start_date": {"type": "string", "format": "date", "description": "Obrigatório se 'collect_questions' estiver nas opções."},
                    "end_date": {"type": "string", "format": "date", "description": "Obrigatório se 'collect_questions' estiver nas opções."},
                    "tags": {"type": "string", "description": "Opcional. Tags separadas por ';' para filtrar a coleta de perguntas."}
                },
                "required": ["options"]
            }
        },
        responses={202: {"description": "Trabalho de mineração iniciado com sucesso."}}
    )
    def create(self, request):
        """
        Inicia um novo trabalho de mineração com base na lista de 'options' fornecida.
        """
        try:
            options = request.data.get('options', [])
            if not options:
                return Response({'error': 'A lista "options" é obrigatória.'}, status=status.HTTP_400_BAD_REQUEST)

            # ... (sua lógica de validação de 'options' continua igual) ...
            
            celery_task_chain = self._build_task_chain(options, request.data)

            if not celery_task_chain:
                return Response({'error': 'Parâmetros insuficientes para as opções.'}, status=status.HTTP_400_BAD_REQUEST)

            # --- MUDANÇA PRINCIPAL AQUI ---
            # Apenas disparamos a tarefa. Não criamos mais o registro Task aqui.
            task_chain_result = celery_task_chain.apply_async()
            
            return Response(
                {'task_id': task_chain_result.id, 'status': 'Trabalho de mineração enviado para a fila'},
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.error(f"Erro ao iniciar trabalho de mineração: {e}", exc_info=True)
            return Response({'error': f'Um erro inesperado ocorreu: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_task_chain(self, options: list, data: dict):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        tags = data.get('tags')

        execution_plan = set(options)
        for opt in options:
            dependencies = OPERATIONS.get(opt, {}).get('dependencies', [])
            execution_plan.update(dependencies)
        
        task_map = {
            'collect_questions': collect_questions_task.s(start_date=start_date, end_date=end_date, tags=tags),
            'repopulate_users': repopulate_users_task.s(),
        }

        ordered_tasks = []
        if 'collect_questions' in execution_plan:
            if not start_date or not end_date:
                return None 
            ordered_tasks.append(task_map['collect_questions'])
        if 'repopulate_users' in execution_plan:
            ordered_tasks.append(task_map['repopulate_users'])
            
        if not ordered_tasks:
            return None
            
        return chain(ordered_tasks)