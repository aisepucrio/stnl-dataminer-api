from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import JiraIssue
from .serializers import JiraIssueSerializer
from .filters import JiraIssueFilter
from jobs.tasks import collect_jira_issues_task
    
class JiraIssueCollectView(APIView):
    def post(self, request, *args, **kwargs):
        jira_domain = request.data.get('jira_domain')
        project_key = request.data.get('project_key')
        jira_email = request.data.get('jira_email')
        jira_api_token = request.data.get('jira_api_token')
        issuetypes = request.data.get('issuetypes', [])  # Tipos de issues a serem coletados (opcional)
        start_date = request.data.get('start_date', None)  # Data de início (opcional)
        end_date = request.data.get('end_date', None)  # Data de fim (opcional)
        
        # Verificação de campos obrigatórios
        if not all([jira_domain, project_key, jira_email, jira_api_token]):
            return Response(
                {"error": "All fields are required: jira_domain, project_key, jira_email, jira_api_token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Chama a tarefa Celery para coletar issues
        task = collect_jira_issues_task.delay(
            jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date, end_date
        )
        
        return Response(
            {"task_id": task.id,
            "message": "Task successfully initiated",
            "instructions": "To check the task status, make a GET request to: "
                          f"http://localhost:8000/jobs/{task.id}/",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
            }, 
            status=status.HTTP_202_ACCEPTED
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