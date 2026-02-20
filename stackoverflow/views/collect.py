from rest_framework import viewsets, status
from rest_framework.response import Response
from datetime import datetime
import logging
from celery import chain

# Import only the active task
from ..tasks import collect_questions_task  # repopulate_users_task is deprecated
from jobs.models import Task
from drf_spectacular.utils import extend_schema  # For API documentation

# Available operations
# Only the question collection task remains active.
# The user enrichment task (repopulate_users) was removed since badge and
# enrichment data are no longer required in this project.
OPERATIONS = {
    'collect_questions': {
        'name': 'Collect Questions',
        'dependencies': []
    },
    # Deprecated / disabled:
    # 'repopulate_users': {
    #     'name': 'Enrich User Data',
    #     'dependencies': ['collect_questions']
    # }
}

logger = logging.getLogger(__name__)


class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet responsible for starting and managing Stack Overflow data
    collection jobs.
    """

    @extend_schema(
        summary="Start a Stack Overflow Mining Job",
        description="""
        Initiates a new asynchronous mining job based on a list of operations.
        This is the primary endpoint for all data collection tasks.
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of operations to perform "
                            "(e.g., ['collect_questions'])."
                        ),
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": (
                            "Required if 'collect_questions' is among options."
                        ),
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": (
                            "Required if 'collect_questions' is among options."
                        ),
                    },
                    "tags": {
                        "type": "string",
                        "description": (
                            "Optional. Tags separated by ';' to filter "
                            "the question collection."
                        ),
                    },
                },
                "required": ["options"],
            }
        },
        responses={202: {"description": "Mining job successfully queued."}},
    )
    def create(self, request):
        """
        Start a new mining job based on the provided 'options' list.
        """
        try:
            options = request.data.get("options", [])
            if not options:
                return Response(
                    {"error": 'The "options" list is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            celery_task_chain = self._build_task_chain(options, request.data)

            if not celery_task_chain:
                return Response(
                    {"error": "Insufficient parameters for the given options."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Trigger the Celery chain
            task_chain_result = celery_task_chain.apply_async()

            return Response(
                {
                    "task_id": task_chain_result.id,
                    "status": "Mining job successfully queued.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            logger.error(f"Error while starting mining job: {e}", exc_info=True)
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Private Methods
    def _build_task_chain(self, options: list, data: dict):
        """
        Builds a Celery task chain based on the requested operations.
        Currently supports only 'collect_questions'.
        """
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        tags = data.get("tags")

        execution_plan = set(options)
        for opt in options:
            dependencies = OPERATIONS.get(opt, {}).get("dependencies", [])
            execution_plan.update(dependencies)

        # Map of available Celery tasks
        task_map = {
            "collect_questions": collect_questions_task.s(
                start_date=start_date, end_date=end_date, tags=tags
            ),
            # Deprecated task:
            # "repopulate_users": repopulate_users_task.s(),
        }

        ordered_tasks = []

        # Question Collection Task
        if "collect_questions" in execution_plan:
            if not start_date or not end_date:
                return None
            ordered_tasks.append(task_map["collect_questions"])

        # Deprecated Enrichment Task
        # if "repopulate_users" in execution_plan:
        #     ordered_tasks.append(task_map["repopulate_users"])

        if not ordered_tasks:
            return None

        # Chain all the selected tasks sequentially
        return chain(ordered_tasks)
