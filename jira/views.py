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
            if not all([jira_domain, project_key, jira_email, jira_api_token]):
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
