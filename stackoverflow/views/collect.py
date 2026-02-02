# In stackoverflow/views/collect.py

from rest_framework import viewsets, status
from rest_framework.response import Response
import logging
from celery import chain
from rest_framework.decorators import action

# Imports from our modules
from ..tasks import collect_questions_task, repopulate_users_task
from drf_spectacular.utils import extend_schema  # For API documentation

# The "menu" of operations lives here
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

# Only the selected Stack Overflow filters are allowed (NO sort/order here)
ALLOWED_FILTER_KEYS = {
    "min", "max",
    "accepted",
    "answers",
    "views",
    "intitle",
    "closed",
    "migrated",
    "nottagged",
    "user",
}


class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet to start and manage Stack Overflow data mining jobs.
    """

    @extend_schema(
        summary="Start a Stack Overflow Mining Job",
        description="""
        Starts a new asynchronous mining job based on a list of operations.
        This is the main endpoint for all data collection and enrichment tasks.
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of operations to execute (e.g. ['collect_questions', 'repopulate_users'])"
                    },
                    "start_date": {"type": "string", "format": "date", "description": "Required if 'collect_questions' is in options."},
                    "end_date": {"type": "string", "format": "date", "description": "Required if 'collect_questions' is in options."},
                    "tags": {"type": "string", "description": "Optional. Tags separated by ';' to filter questions."},
                    "filters": {
                        "type": "object",
                        "description": "Optional. Only these keys are allowed: min, max, accepted, answers, views, intitle, closed, migrated, nottagged, user."
                    }
                },
                "required": ["options"]
            }
        },
        responses={202: {"description": "Mining job successfully queued."}}
    )
    def create(self, request):
        """
        Starts a new mining job based on the provided 'options'.
        """
        try:
            options = request.data.get('options', [])
            if not options:
                return Response({'error': 'The "options" list is required.'}, status=status.HTTP_400_BAD_REQUEST)

            celery_task_chain = self._build_task_chain(options, request.data)

            if not celery_task_chain:
                return Response({'error': 'Insufficient parameters for the selected options.'},
                                status=status.HTTP_400_BAD_REQUEST)

            task_chain_result = celery_task_chain.apply_async()

            return Response(
                {'task_id': task_chain_result.id, 'status': 'Mining job sent to queue'},
                status=status.HTTP_202_ACCEPTED
            )

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error starting mining job: {e}", exc_info=True)
            return Response({'error': f'An unexpected error occurred: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ✅ NEW: advanced route that reuses the same payload but signals "advanced" mode.
    # This does NOT change existing behavior of create(); it adds a new endpoint.
    @action(detail=False, methods=["post"], url_path="advanced")
    def advanced(self, request):
        """
        Starts a new mining job using the advanced Stack Exchange endpoint.
        """
        try:
            options = request.data.get('options', [])
            if not options:
                return Response({'error': 'The "options" list is required.'}, status=status.HTTP_400_BAD_REQUEST)

            celery_task_chain = self._build_task_chain(options, request.data, mode="advanced")

            if not celery_task_chain:
                return Response({'error': 'Insufficient parameters for the selected options.'},
                                status=status.HTTP_400_BAD_REQUEST)

            task_chain_result = celery_task_chain.apply_async()

            return Response(
                {'task_id': task_chain_result.id, 'status': 'Mining job sent to queue'},
                status=status.HTTP_202_ACCEPTED
            )

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error starting mining job (advanced): {e}", exc_info=True)
            return Response({'error': f'An unexpected error occurred: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_task_chain(self, options: list, data: dict, mode: str = "default"):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        tags = data.get('tags')
        filters = data.get('filters')

        # Minimal validation: filters must be a dict and only contain allowed keys
        if filters is not None:
            if not isinstance(filters, dict):
                raise ValueError('The "filters" field must be an object (JSON dictionary).')

            extra_keys = set(filters.keys()) - ALLOWED_FILTER_KEYS
            if extra_keys:
                raise ValueError(f"Unsupported filters: {', '.join(sorted(extra_keys))}")

        execution_plan = set(options)
        for opt in options:
            dependencies = OPERATIONS.get(opt, {}).get('dependencies', [])
            execution_plan.update(dependencies)

        task_map = {
            'collect_questions': collect_questions_task.s(
                start_date=start_date,
                end_date=end_date,
                tags=tags,
                filters=filters,
                mode=mode,
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
