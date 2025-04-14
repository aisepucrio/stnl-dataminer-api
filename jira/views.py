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
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

# Configuração de logs para debug
logger = logging.getLogger(__name__)

class JiraIssueCollectView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            jira_domain = request.data.get('jira_domain')
            project_key = request.data.get('project_key')
            issuetypes = request.data.get('issuetypes', [])  
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            # Captura variáveis do .env
            jira_email = settings.JIRA_EMAIL
            jira_api_token = settings.JIRA_API_TOKEN

            # Debug: Verifica se as credenciais do JIRA foram carregadas corretamente
            logger.info(f"JIRA Email: {jira_email}")
            logger.info(f"JIRA API Token: {jira_api_token[:5]}*****")  # Esconde parte do token por segurança

            # Validação de campos obrigatórios
            if not all([jira_domain, project_key]):
                return Response(
                    {"error": "Missing required fields: jira_domain, project_key, jira_email, jira_api_token"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Inicia a tarefa Celery (Removido jira_email e jira_api_token da chamada)
            task = collect_jira_issues_task.delay(
                jira_domain,
                project_key,
                issuetypes if issuetypes else [],  # Garante que sempre seja uma lista
                start_date,
                end_date
            )

            return Response(
                {
                    "task_id": task.id,
                    "message": "Task successfully initiated",
                    "status_endpoint": f"http://localhost:8000/api/jobs/task/{task.id}/"
                },
                status=status.HTTP_202_ACCEPTED
            )
        
        except Exception as e:
            logger.error(f"Erro no JiraIssueCollectView: {e}", exc_info=True)
            return Response(
                {"error": "Internal Server Error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class JiraIssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = JiraIssueFilter
    search_fields = ['summary', 'description', 'creator', 'assignee']
    ordering_fields = ['created', 'updated', 'priority', 'status']

class JiraIssueDetailView(generics.RetrieveAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    lookup_field = 'issue_key'


@extend_schema(
    summary="Jira Dashboard statistics",
    description="Provides statistics about Jira issues. "
                "If project_id is provided, returns detailed stats for that project.",
    parameters=[
        OpenApiParameter(
            name="project_id",
            description="ID of the project to get statistics for. If not provided, returns aggregated stats for all projects.",
            required=False,
            type=int
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
                "project_id": {"type": "integer", "nullable": True},
                "project_name": {"type": "string", "nullable": True},
                "issues_count": {"type": "integer"},
                "time_mined": {"type": "string", "format": "date-time", "nullable": True},
                "projects_count": {"type": "integer", "nullable": True},
                "projects": {
                    "type": "array", 
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "project": {"type": "string"}
                        }
                    },
                    "nullable": True
                }
            }
        },
        404: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            }
        }
    },
    examples=[
        OpenApiExample(
            "Project Example",
            value={
                "project_id": 1,
                "project_name": "Sample Project",
                "issues_count": 120,
                "time_mined": "2023-01-01T12:00:00Z"
            },
            summary="Example with project_id"
        ),
        OpenApiExample(
            "All Projects Example",
            value={
                "issues_count": 500,
                "projects_count": 5,
                "projects": [
                    {"id": 1, "project": "Project One"},
                    {"id": 2, "project": "Project Two"}
                ]
            },
            summary="Example without project_id"
        )
    ]
)
class JiraDashboardView(APIView):
    def get(self, request):
        project_id = request.query_params.get('project_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        filters = {
            'created__gte': start_date,
            'created__lte': end_date
        }
        
        
        issues_query = JiraIssue.objects.filter(**filters)
        
        if project_id:
            try:
                project_issues = issues_query.filter(project__id=project_id)
                
                project_name = project_id
                if project_issues.exists():
                    project_name = project_issues.first().project
                
                response_data = {
                    "project_id": project_id,
                    "project_name": project_name,
                    "issues_count": project_issues.count(),
                    "time_mined": timezone.now().isoformat()
                }
            except Exception as e:
                return Response(
                    {"error": f"Error retrieving project with ID {project_id}: {str(e)}"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            projects = issues_query.values('project').distinct()
            projects_list = [{"id": p['id'], "project": p['project']} for p in projects]
            
            response_data = {
                "issues_count": issues_query.count(),
                "projects_count": len(projects_list),
                "projects": projects_list
            }
        
        return Response(response_data)
