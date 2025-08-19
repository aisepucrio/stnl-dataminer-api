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
    description="Initiates a task to collect issues from a Jira project",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'jira_domain': {'type': 'string', 'description': 'Jira instance domain'},
                'project_key': {'type': 'string', 'description': 'Jira project key'},
                'issuetypes': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of issue types to collect'},
                'start_date': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'end_date': {'type': 'string', 'format': 'date-time', 'nullable': True}
            },
            'required': ['jira_domain', 'project_key']
        }
    },
    responses={
        202: {
            'type': 'object',
            'properties': {
                'task_id': {'type': 'string'},
                'message': {'type': 'string'},
                'status_endpoint': {'type': 'string'}
            }
        },
        400: {'description': 'Missing required fields'},
        500: {'description': 'Internal server error'}
    }
)
class JiraIssueCollectView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            projects = request.data.get('projects', [])
        
            if not projects:
                return Response({"error": "No project provided."}, status=400)

            for project_info in projects:
                jira_domain = project_info.get('jira_domain')
                project_key = project_info.get('project_key')

                if not jira_domain or not project_key:
                    return Response({"error": "Each project must contain 'jira_domain' and 'project'."}, status=400)

            issuetypes = request.data.get('issuetypes', [])  
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            # Get variables from .env
            jira_email = settings.JIRA_EMAIL
            jira_api_token = settings.JIRA_API_TOKEN

            # Debug: Check if JIRA credentials were loaded correctly
            logger.info(f"JIRA Email: {jira_email}")
            logger.info(f"JIRA API Token: {jira_api_token[:5]}*****")  # Hides part of the token for security

            # Validation of required fields
            if not all([jira_domain, project_key]):
                return Response(
                    {"error": "Missing required fields: jira_domain, project_key, jira_email, jira_api_token"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Start Celery task (Removed jira_email and jira_api_token from the call)
            tasks = []

            for project_info in projects:
                jira_domain = project_info.get('jira_domain')
                project_key = project_info.get('project_key')

                if not jira_domain or not project_key:
                    return Response(
                        {"error": "Each project must contain 'jira_domain' and 'project'."},
                        status=400
                    )

                task = collect_jira_issues_task.delay(
                    jira_domain,
                    project_key,
                    issuetypes if issuetypes else [], 
                    start_date,
                    end_date
                )

                Task.objects.create(
                    task_id=task.id,
                    operation='collect_jira_issues',
                    repository=f"{jira_domain}/{project_key}",
                    status='PENDING'
                )

                tasks.append({
                    "task_id": task.id,
                    "repository": f"{jira_domain}/{project_key}"
                })


            return Response(
                {
                    "task_id": task.id,
                    "message": "Task successfully initiated",
                    "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
                },
                status=status.HTTP_202_ACCEPTED
            )
        
        except Exception as e:
            logger.error(f"Error in JiraIssueCollectView: {e}", exc_info=True)
            return Response(
                {"error": "Internal Server Error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )