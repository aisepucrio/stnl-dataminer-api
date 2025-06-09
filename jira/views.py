from django.conf import settings
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import generics, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.models import Task
from .tasks import fetch_issues, fetch_metadata
from .filters import JiraIssueFilter
from .models import JiraIssue, JiraProject, JiraSprint, JiraComment, JiraCommit
from .serializers import JiraIssueSerializer, JiraIssueCollectSerializer

import logging

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
            projects = request.data.get('projects', [])
        
            if not projects:
                return Response({"error": "No projects provided."}, status=400)

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

                task = fetch_issues.delay(
                    project_key,
                    jira_domain,
                    start_date,
                    end_date,
                    depth='basic'
                )

                Task.objects.create(
                    task_id=task.id,
                    operation='fetch_issues',
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
                    "items": {
                        "type": "object",
                        "properties": { 
                            "id": {"type": "string"},
                            "name": {"type": "string"}
                        }
                    },
                    "nullable": True
                },
                "sprints_count": {"type": "integer", "nullable": True}, # Added
                "comments_count": {"type": "integer", "nullable": True}, # Added
                "commits_count": {"type": "integer", "nullable": True}  # Added
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
                "time_mined": "2023-01-01T12:00:00Z",
                "sprints_count": 5,
                "comments_count": 250,
                "commits_count": 80
            },
            summary="Example with project_id"
        ),
        OpenApiExample(
            "All Projects Example",
            value={
                "issues_count": 500,
                "projects_count": 3,
                "projects": [
                    {"id": "1", "name": "Project One"},
                    {"id": "2", "name": "Project Two"},
                    {"id": "3", "name": "Project Three"}
                ],
                "sprints_count": 15,
                "comments_count": 750,
                "commits_count": 300
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
            project_id = request.query_params.get('project_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            filters = {}

            if start_date:
                filters['created__gte'] = start_date
            if end_date:
                filters['created__lte'] = end_date

            issues_query = JiraIssue.objects.filter(**filters)

            if project_id:
                try:
                    project = JiraProject.objects.get(id=project_id)
                    project_issues = issues_query.filter(project=project)

                    if project_issues.exists():
                        latest_time_mined = project_issues.order_by('-time_mined').first().time_mined
                    else:
                        latest_time_mined = None

                    sprints_count = JiraSprint.objects.filter(issue__in=project_issues).count()
                    comments_count = JiraComment.objects.filter(issue__in=project_issues).count()
                    commits_count = JiraCommit.objects.filter(issue__in=project_issues).count()

                    response_data = {
                        "project_name": project.name,
                        "issues_count": project_issues.count(),
                        "time_mined": latest_time_mined.isoformat() if latest_time_mined else None,
                        "sprints_count": sprints_count,
                        "comments_count": comments_count,
                        "commits_count": commits_count
                    }
                except JiraProject.DoesNotExist:
                    return Response(
                        {"error": f"Project with ID {project_id} not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                except Exception as e: # Catching generic exception for project specific data retrieval
                    return Response(
                        {"error": f"Error retrieving data for project ID {project_id}: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                projects = JiraProject.objects.all()
                projects_list = [{"id": p.id, "name": p.name} for p in projects]

                sprints_count = JiraSprint.objects.filter(issue__in=issues_query).count()
                comments_count = JiraComment.objects.filter(issue__in=issues_query).count()
                commits_count = JiraCommit.objects.filter(issue__in=issues_query).count()

                response_data = {
                    "issues_count": issues_query.count(),
                    "projects_count": len(projects_list),
                    "projects": projects_list,
                    "sprints_count": sprints_count,
                    "comments_count": comments_count,
                    "commits_count": commits_count
                }

            return Response(response_data)
        except Exception as e:
            print(e)
            return Response({"error": "An internal server error occurred. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(
    tags=['Jira'],
    summary="Graph Dashboard Data",
    description="Provides cumulative time-series data for issues, comments, commits, and sprints",
    parameters=[
        OpenApiParameter(
            name='project_id',
            description='ID of the project to get statistics for',
            required=False,
            type=str
        ),
        OpenApiParameter(
            name='start_date',
            description='Filter display range from this date onwards (ISO format)',
            required=False,
            type=OpenApiTypes.DATETIME
        ),
        OpenApiParameter(
            name='end_date',
            description='Filter display range up to this date (ISO format)',
            required=False,
            type=OpenApiTypes.DATETIME
        ),
        OpenApiParameter(
            name='interval',
            description='Time interval for grouping (day, month, year)',
            required=False,
            type=str,
            default='day'
        )
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "nullable": True},
                "project_name": {"type": "string", "nullable": True},
                "time_series": {
                    "type": "object",
                    "properties": {
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "issues": {"type": "array", "items": {"type": "integer"}},
                        "comments": {"type": "array", "items": {"type": "integer"}},
                        "commits": {"type": "array", "items": {"type": "integer"}},
                        "sprints": {"type": "array", "items": {"type": "integer"}}
                    }
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            "Project Example",
            value={
                "project_id": "123",
                "project_name": "Sample Project",
                "time_series": {
                    "labels": ["2023-01-01", "2023-01-02", "2023-01-03"],
                    "issues": [5, 12, 15],
                    "comments": [2, 6, 7],
                    "commits": [1, 1, 3],
                    "sprints": [0, 1, 1]
                }
            },
            summary="Example with project_id showing cumulative counts"
        ),
        OpenApiExample(
            "All Projects Example",
            value={
                "time_series": {
                    "labels": ["2023-01-01", "2023-01-02", "2023-01-03"],
                    "issues": [10, 22, 30],
                    "comments": [5, 11, 14],
                    "commits": [2, 3, 6],
                    "sprints": [1, 1, 2]
                }
            },
            summary="Example without project_id showing cumulative counts"
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
class JiraGraphDashboardView(APIView):
    def get(self, request):
        try:
            project_id = request.query_params.get('project_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            interval = request.query_params.get('interval', 'day')

            # Determine the truncation function and date format based on interval
            if interval == 'day':
                trunc_func = TruncDay
                date_format = '%Y-%m-%d'
            elif interval == 'month':
                trunc_func = TruncMonth
                date_format = '%Y-%m'
            else:
                trunc_func = TruncYear
                date_format = '%Y'

            # Base queryset filters for display range
            display_filters = {}
            if start_date:
                display_filters['created__gte'] = start_date
            if end_date:
                display_filters['created__lte'] = end_date
            if project_id:
                display_filters['project_id'] = project_id

            # Project filter for cumulative counts
            project_filter = {'project_id': project_id} if project_id else {}

            # Get cumulative data for each date in the display range
            issues_data = []
            comments_data = []
            commits_data = []
            sprints_data = []
            
            base_issues = JiraIssue.objects.filter(**project_filter)
            base_comments = JiraComment.objects.filter(issue__in=base_issues)
            base_commits = JiraCommit.objects.filter(issue__in=base_issues)
            base_sprints = JiraSprint.objects.filter(issue__in=base_issues)

            # Get the date range for display
            display_issues = base_issues.filter(**display_filters)
            dates = display_issues.annotate(
                interval=trunc_func('created')
            ).values('interval').distinct().order_by('interval')

            for date in dates:
                current_date = date['interval']
                
                # Count all items up to this date
                issues_count = base_issues.filter(created__lte=current_date).count()
                comments_count = base_comments.filter(created__lte=current_date).count()
                commits_count = base_commits.filter(timestamp__lte=current_date).count()
                sprints_count = base_sprints.filter(startDate__lte=current_date).count()

                formatted_date = current_date.strftime(date_format)
                issues_data.append({'interval': formatted_date, 'count': issues_count})
                comments_data.append({'interval': formatted_date, 'count': comments_count})
                commits_data.append({'interval': formatted_date, 'count': commits_count})
                sprints_data.append({'interval': formatted_date, 'count': sprints_count})

            # Convert to response format
            date_range = [item['interval'] for item in issues_data]
            issues_list = [item['count'] for item in issues_data]
            comments_list = [item['count'] for item in comments_data]
            commits_list = [item['count'] for item in commits_data]
            sprints_list = [item['count'] for item in sprints_data]

            # Get project name if needed
            project_name = None
            if project_id:
                try:
                    project = JiraProject.objects.get(id=project_id)
                    project_name = project.name
                except JiraProject.DoesNotExist:
                    project_name = None

            response_data = {
                "time_series": {
                    "labels": date_range,
                    "issues": issues_list,
                    "comments": comments_list,
                    "commits": commits_list,
                    "sprints": sprints_list
                }
            }
            if project_id:
                response_data["project_id"] = project_id
                response_data["project_name"] = project_name

            return Response(response_data)

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )