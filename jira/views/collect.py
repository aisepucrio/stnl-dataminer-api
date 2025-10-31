import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.models import Task
from jira.tasks import collect_jira_issues_task


logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Jira'],
    summary="Collect Jira Issues",
    description="Initiates a task to collect issues from one or more Jira projects.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'projects': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'jira_domain': {'type': 'string', 'description': 'Jira instance domain'},
                            'project_key': {'type': 'string', 'description': 'Jira project key'}
                        },
                        'required': ['jira_domain', 'project_key']
                    },
                    'description': 'List of Jira projects to collect issues from'
                },
                'issuetypes': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of issue types to collect'
                },
                'start_date': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'end_date': {'type': 'string', 'format': 'date-time', 'nullable': True}
            },
            'required': ['projects']
        }
    },
    responses={
        202: {
            'type': 'object',
            'properties': {
                'tasks': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'task_id': {'type': 'string'},
                            'repository': {'type': 'string'}
                        }
                    }
                },
                'message': {'type': 'string'}
            }
        },
        400: {'description': 'Missing or invalid required fields'},
        500: {'description': 'Internal server error'}
    }
)
class JiraIssueCollectView(APIView):
    """
    API endpoint that initiates Celery tasks to collect issues from Jira projects.
    """

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            projects = data.get('projects', [])

            # 1. Validate that 'projects' is a list
            if not isinstance(projects, list):
                return Response(
                    {"error": "'projects' must be a list of objects"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not projects:
                return Response({"error": "No project provided."}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Validate that each item in 'projects' is a dict with required keys
            for project_info in projects:
                if not isinstance(project_info, dict) or "jira_domain" not in project_info or "project_key" not in project_info:
                    return Response(
                        {"error": "Each project must be an object containing 'jira_domain' and 'project_key'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 3. Validate the type of 'issuetypes'
            issuetypes = data.get('issuetypes', [])
            if issuetypes is not None and not isinstance(issuetypes, list):
                return Response(
                    {"error": "'issuetypes' must be a list"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            start_date = data.get('start_date', None)
            end_date = data.get('end_date', None)

            # 4. Load Jira credentials from environment variables
            jira_email = settings.JIRA_EMAIL
            jira_api_token = settings.JIRA_API_TOKEN

            logger.info(f"JIRA Email: {jira_email}")
            logger.info(f"JIRA API Token: {jira_api_token[:5]}*****")

            # Validate credentials
            if not jira_email or not jira_api_token:
                return Response(
                    {"error": "Missing JIRA credentials in settings."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 5. Trigger Celery tasks
            tasks = []
            for project_info in projects:
                jira_domain = project_info['jira_domain']
                project_key = project_info['project_key']

                task = collect_jira_issues_task.delay(
                    jira_domain,
                    project_key,
                    issuetypes if issuetypes else [],
                    start_date,
                    end_date
                )

                tasks.append({
                    "task_id": task.id,
                    "repository": f"{jira_domain}/{project_key}"
                })

            # Return 202 response
            return Response(
                {
                    "tasks": tasks,
                    "message": "Task(s) successfully initiated"
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.error(f"Error in JiraIssueCollectView: {e}", exc_info=True)
            return Response(
                {"error": "Internal Server Error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
