from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import JiraIssue
from .serializers import JiraIssueSerializer, JiraIssueCollectSerializer
from .filters import JiraIssueFilter
from jobs.tasks import collect_jira_issues_task
from django.conf import settings
import logging
from jobs.models import Task
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

# Debug logging configuration
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
            jira_domain = request.data.get('jira_domain')
            project_key = request.data.get('project_key')
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
            task = collect_jira_issues_task.delay(
                jira_domain,
                project_key,
                issuetypes if issuetypes else [],  # Ensures it's always a list
                start_date,
                end_date
            )
            
            # Save tasks on database
            Task.objects.create(
                task_id=task.id,
                operation='collect_jira_issues',
                repository=f"{jira_domain}/{project_key}",
                status='PENDING'
            )

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

@extend_schema(
    tags=['Jira'],
    summary="List Jira Issues",
    description="Returns a paginated list of Jira issues with filtering and search capabilities",
    parameters=[
        OpenApiParameter(
            name='search',
            description='Search in summary, description, creator, and assignee fields',
            required=False,
            type=str
        ),
        OpenApiParameter(
            name='ordering',
            description='Order by created, updated, priority, or status (prefix with - for descending)',
            required=False,
            type=str
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer'},
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'issue_id': {'type': 'string'},
                            'issue_key': {'type': 'string'},
                            'issuetype': {'type': 'string'},
                            'project': {'type': 'string'},
                            'priority': {'type': 'string', 'nullable': True},
                            'status': {'type': 'string'},
                            'assignee': {'type': 'string', 'nullable': True},
                            'creator': {'type': 'string'},
                            'created': {'type': 'string', 'format': 'date-time'},
                            'updated': {'type': 'string', 'format': 'date-time'},
                            'summary': {'type': 'string'},
                            'description': {'type': 'string', 'nullable': True},
                            'history': {'type': 'array', 'items': {'type': 'object'}},
                            'activity_log': {'type': 'array', 'items': {'type': 'object'}},
                            'checklist': {'type': 'array', 'items': {'type': 'object'}},
                            'history_formatted': {'type': 'array', 'items': {'type': 'object'}},
                            'activity_log_formatted': {'type': 'array', 'items': {'type': 'object'}},
                            'checklist_formatted': {'type': 'array', 'items': {'type': 'object'}}
                        }
                    }
                }
            }
        }
    }
)
class JiraIssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = JiraIssueFilter
    search_fields = ['summary', 'description', 'creator', 'assignee']
    ordering_fields = ['created', 'updated', 'priority', 'status']

@extend_schema(
    tags=['Jira'],
    summary="Retrieve Jira Issue",
    description="Returns detailed information about a specific Jira issue",
    parameters=[
        OpenApiParameter(
            name='issue_key',
            description='The Jira issue key (e.g., PROJECT-123)',
            required=True,
            type=str,
            location=OpenApiParameter.PATH
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'issue_id': {'type': 'string'},
                'issue_key': {'type': 'string'},
                'issuetype': {'type': 'string'},
                'project': {'type': 'string'},
                'priority': {'type': 'string', 'nullable': True},
                'status': {'type': 'string'},
                'assignee': {'type': 'string', 'nullable': True},
                'creator': {'type': 'string'},
                'created': {'type': 'string', 'format': 'date-time'},
                'updated': {'type': 'string', 'format': 'date-time'},
                'summary': {'type': 'string'},
                'description': {'type': 'string', 'nullable': True},
                'history': {'type': 'array', 'items': {'type': 'object'}},
                'activity_log': {'type': 'array', 'items': {'type': 'object'}},
                'checklist': {'type': 'array', 'items': {'type': 'object'}},
                'history_formatted': {'type': 'array', 'items': {'type': 'object'}},
                'activity_log_formatted': {'type': 'array', 'items': {'type': 'object'}},
                'checklist_formatted': {'type': 'array', 'items': {'type': 'object'}}
            }
        },
        404: {'description': 'Issue not found'}
    }
)
class JiraIssueDetailView(generics.RetrieveAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    lookup_field = 'issue_key'


@extend_schema(
    tags=['Jira'],
    summary="Jira Dashboard statistics",
    description="Provides statistics about Jira issues. "
                "If project_name is provided, returns detailed stats for that project.",
    parameters=[
        OpenApiParameter(
            name="project_name",
            description="Name of the project to get statistics for. If not provided, returns aggregated stats for all projects.",
            required=False,
            type=str
        ),
        OpenApiParameter(
            name="start_date",
            description="Filter data from this date onwards (ISO format). Defaults to 1970-01-01.",
            required=False,
            type=OpenApiTypes.DATETIME
        ),
        OpenApiParameter(
            name="end_date",
            description="Filter data up to this date (ISO format). Defaults to current time.",
            required=False,
            type=OpenApiTypes.DATETIME
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "nullable": True},
                "issues_count": {"type": "integer"},
                "time_mined": {"type": "string", "format": "date-time", "nullable": True},
                "projects_count": {"type": "integer", "nullable": True},
                "projects": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "nullable": True
                }
            }
        },
        400: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            },
            "description": "Invalid request parameters (invalid date format)"
        },
        404: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            },
            "description": "Project not found"
        },
        500: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            },
            "description": "Internal server error"
        }
    },
    examples=[
        OpenApiExample(
            "Project Example",
            value={
                "project_name": "Sample Project",
                "issues_count": 120,
                "time_mined": "2023-01-01T12:00:00Z"
            },
            summary="Example with project_name"
        ),
        OpenApiExample(
            "All Projects Example",
            value={
                "issues_count": 500,
                "projects_count": 5,
                "projects": ["Project One", "Project Two", "Project Three"]
            },
            summary="Example without project_name"
        ),
        OpenApiExample(
            "Error Example - Invalid Date",
            value={
                "error": "Invalid start_date format. Please use ISO format (YYYY-MM-DDTHH:MM:SSZ)."
            },
            summary="Example of invalid date format error",
            response_only=True,
            status_codes=["400"]
        )
    ]
)
class JiraDashboardView(APIView):
    def get(self, request):
        try:
            project_name = request.query_params.get('project_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            filters = {}

            if start_date:
                filters['created__gte'] = start_date
            if end_date:
                filters['created__lte'] = end_date

            issues_query = JiraIssue.objects.filter(**filters)

            if project_name:
                try:
                    project_issues = issues_query.filter(project=project_name)

                    if project_issues.exists():
                        project_name = project_issues.first().project
                        latest_time_mined = project_issues.order_by('-time_mined').first().time_mined
                    else:
                        latest_time_mined = None

                    response_data = {
                        "project_name": project_name,
                        "issues_count": project_issues.count(),
                        "time_mined": latest_time_mined.isoformat()
                    }
                except Exception as e:
                    return Response(
                        {"error": f"Error retrieving project with ID {project_id}: {str(e)}"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                projects = issues_query.values('project').distinct()
                projects_list = [p['project'] for p in projects]

                response_data = {
                    "issues_count": issues_query.count(),
                    "projects_count": len(projects_list),
                    "projects": projects_list
                }


            return Response(response_data)
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
