from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import JiraIssueType, JiraIssue
from .serializers import JiraIssueSerializer, JiraIssueTypeSerializer
from jobs.tasks import collect_issue_types_task, collect_jira_issues_task
    
class IssueCollectView(APIView):
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
            {"status": "Issue collection started", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED
        )

class IssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer

class IssueDetailView(generics.RetrieveAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    lookup_field = 'issue_id'

class IssueDeleteView(generics.DestroyAPIView):
    queryset = JiraIssue.objects.all()
    lookup_field = 'issue_id'
    
    def delete(self, request, *args, **kwargs):
        issue = self.get_object()
        self.perform_destroy(issue)
        return Response({"status": "Issue deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class IssueTypeCollectView(APIView):
    def post(self, request, *args, **kwargs):
        jira_domain = request.data.get('jira_domain')
        jira_email = request.data.get('jira_email')
        jira_api_token = request.data.get('jira_api_token')
        
        # Verificação de campos obrigatórios
        if not all([jira_domain, jira_email, jira_api_token]):
            return Response(
                {"error": "All fields are required: jira_domain, jira_email, jira_api_token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Chama a tarefa Celery para coletar issue types
        task = collect_issue_types_task.delay(jira_domain, jira_email, jira_api_token)
        
        return Response(
            {"status": "Issue type collection started", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED
        )

class IssueTypeListView(generics.ListAPIView):
    queryset = JiraIssueType.objects.all()
    serializer_class = JiraIssueTypeSerializer

class IssueTypeDetailView(generics.RetrieveAPIView):
    queryset = JiraIssueType.objects.all()
    serializer_class = JiraIssueTypeSerializer
    lookup_field = 'issuetype_id'

class IssueTypeDeleteView(generics.DestroyAPIView):
    queryset = JiraIssueType.objects.all()
    lookup_field = 'issuetype_id'
    
    def delete(self, request, *args, **kwargs):
        issuetype = self.get_object()
        self.perform_destroy(issuetype)
        return Response({"status": "Issue type deleted successfully"}, status=status.HTTP_204_NO_CONTENT)