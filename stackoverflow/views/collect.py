from rest_framework import viewsets, status
from rest_framework.response import Response
from datetime import datetime
import logging
from celery import chain
from ..tasks import collect_questions_task, repopulate_users_task
from jobs.models import Task
from drf_spectacular.utils import extend_schema

OPERATIONS = {
    'collect_questions': {
        'name': 'Collect New Questions',
        'dependencies': []
    },
    'repopulate_users': {
        'name': 'Enrich User Data',
        'dependencies': ['collect_questions']
    }
}

logger = logging.getLogger(__name__)


class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet to initiate and manage Stack Overflow data collection tasks.
    """

    @extend_schema(
        summary="Start a Stack Overflow Mining Job",
        description="""
        Initiates a new asynchronous data mining job based on a list of selected operations.
        This is the main endpoint for launching data collection and enrichment tasks.
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of operations to execute (e.g., ['collect_questions', 'repopulate_users'])."
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Required if 'collect_questions' is included in options."
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Required if 'collect_questions' is included in options."
                    },
                    "tags": {
                        "type": "string",
                        "description": "Optional. Semicolon-separated tags to filter question collection."
                    }
                },
                "required": ["options"]
            }
        },
        responses={202: {"description": "Mining job successfully started."}}
    )
    def create(self, request):
        """
        Starts a new Stack Overflow mining job based on the provided 'options' list.
        """
        try:
            options = request.data.get('options', [])
            if not options:
                return Response(
                    {'error': 'The "options" list is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            celery_task_chain = self._build_task_chain(options, request.data)

            if not celery_task_chain:
                return Response(
                    {'error': 'Insufficient parameters for the selected options.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            task_chain_result = celery_task_chain.apply_async()

            return Response(
                {
                    'task_id': task_chain_result.id,
                    'status': 'Mining job successfully queued.'
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.error(f"Error starting mining job: {e}", exc_info=True)
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _build_task_chain(self, options: list, data: dict):
        """
        Builds a Celery task chain based on selected operations and dependencies.
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        tags = data.get('tags')

        # Build execution plan including dependencies
        execution_plan = set(options)
        for opt in options:
            dependencies = OPERATIONS.get(opt, {}).get('dependencies', [])
            execution_plan.update(dependencies)

        task_map = {
            'collect_questions': collect_questions_task.s(
                start_date=start_date, end_date=end_date, tags=tags
            ),
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
