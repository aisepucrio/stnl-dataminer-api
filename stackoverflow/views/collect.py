from rest_framework import viewsets, status
from rest_framework.response import Response
import logging
from celery import chain
from rest_framework.decorators import action

from ..tasks import collect_questions_task  # repopulate_users_task is deprecated
from drf_spectacular.utils import extend_schema  # For API documentation

# Available operations
OPERATIONS = {
    "collect_questions": {"name": "Collect Questions", "dependencies": []},
    # Deprecated / disabled:
    # "repopulate_users": {"name": "Enrich User Data", "dependencies": ["collect_questions"]},
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

ALLOWED_MODES = {"default", "advanced"}


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
                        "description": "List of operations to perform (e.g., ['collect_questions']).",
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Required if 'collect_questions' is among options.",
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Required if 'collect_questions' is among options.",
                    },
                    "tags": {
                        "description": "Optional. Tags filter. Accepts 'python;django' or ['python','django'].",
                        "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                    },
                    "filters": {
                        "type": "object",
                        "description": (
                            "Optional. Only these keys are allowed: min, max, accepted, answers, "
                            "views, intitle, closed, migrated, nottagged, user."
                        ),
                    },
                    "mode": {
                        "type": "string",
                        "description": "Optional. Mining mode: 'default' or 'advanced'.",
                        "enum": ["default", "advanced"],
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

            mode = request.data.get("mode", "default")
            if mode not in ALLOWED_MODES:
                return Response(
                    {"error": f'Invalid "mode". Allowed: {sorted(ALLOWED_MODES)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            celery_task_chain = self._build_task_chain(options, request.data, mode=mode)

            if not celery_task_chain:
                return Response(
                    {"error": "Insufficient parameters for the given options."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            task_chain_result = celery_task_chain.apply_async()

            return Response(
                {"task_id": task_chain_result.id, "status": "Mining job successfully queued."},
                status=status.HTTP_202_ACCEPTED,
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error while starting mining job: {e}", exc_info=True)
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Advanced route that reuses the same payload but forces "advanced" mode.
    @action(detail=False, methods=["post"], url_path="advanced")
    def advanced(self, request):
        """
        Starts a new mining job using the advanced Stack Exchange endpoint.
        """
        try:
            options = request.data.get("options", [])
            if not options:
                return Response(
                    {"error": 'The "options" list is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            celery_task_chain = self._build_task_chain(options, request.data, mode="advanced")

            if not celery_task_chain:
                return Response(
                    {"error": "Insufficient parameters for the selected options."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            task_chain_result = celery_task_chain.apply_async()

            return Response(
                {"task_id": task_chain_result.id, "status": "Mining job sent to queue"},
                status=status.HTTP_202_ACCEPTED,
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error starting mining job (advanced): {e}", exc_info=True)
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Private Methods
    def _build_task_chain(self, options: list, data: dict, mode: str = "default"):
        """
        Builds a Celery task chain based on the requested operations.
        Currently supports only 'collect_questions'.
        """
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        tags = data.get("tags")
        filters = data.get("filters")

        # Minimal validation: filters must be a dict and only contain allowed keys
        if filters is not None:
            if not isinstance(filters, dict):
                raise ValueError('The "filters" field must be an object (JSON dictionary).')

            extra_keys = set(filters.keys()) - ALLOWED_FILTER_KEYS
            if extra_keys:
                raise ValueError(f"Unsupported filters: {', '.join(sorted(extra_keys))}")

        execution_plan = set(options)
        for opt in options:
            dependencies = OPERATIONS.get(opt, {}).get("dependencies", [])
            execution_plan.update(dependencies)

        task_map = {
            "collect_questions": collect_questions_task.s(
                start_date=start_date,
                end_date=end_date,
                tags=tags,
                filters=filters,
                mode=mode,
            ),
        }

        ordered_tasks = []

        if "collect_questions" in execution_plan:
            if not start_date or not end_date:
                return None
            ordered_tasks.append(task_map["collect_questions"])

        if not ordered_tasks:
            return None

        return chain(ordered_tasks)