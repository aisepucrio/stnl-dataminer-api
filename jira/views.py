from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from jobs.models import Task
from .models import JiraIssueType, JiraIssue
from .serializers import JiraIssueSerializer, JiraIssueTypeSerializer
from .tasks import collect_issue_types, collect_jira_issues

class IssueCollectView(APIView):
    def post(self, request, *args, **kwargs):
        jira_domain = request.data.get('jira_domain')
        project_key = request.data.get('project_key')
        jira_email = request.data.get('jira_email')
        jira_api_token = request.data.get('jira_api_token')
        issuetypes = request.data.get('issuetypes', []) # Tipos de issues a serem coletados (opcional)
        start_date = request.data.get('start_date', None)  # Data de início (opcional)
        end_date = request.data.get('end_date', None)  # Data de fim (opcional)
        # print(jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date, end_date)
        
        if not all([project_key, jira_domain, jira_email, jira_api_token]):
            return Response({"error": "All fields are required, including issue_types"}, status=status.HTTP_400_BAD_REQUEST)
        
        task = Task.objects.create(
            status=Task.Status.PENDING,
            metadata={
                'project_key': project_key,
                'issuetypes': issuetypes,
                'start_date': start_date,
                'end_date': end_date
            }
        )

        # Chama a tarefa Celery para minerar issues
        collect_jira_issues.delay(jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date, end_date, task.id)
        
        return Response({"status": "Issue collection started", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

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
        print(jira_domain, jira_email, jira_api_token)
        
        if not all([jira_domain, jira_email, jira_api_token]):
            return Response({"error": "Missing parameters: jira_domain, jira_email, and jira_api_token are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Cria a task no banco de dados
        task = Task.objects.create(
            status=Task.Status.PENDING,
            metadata={'operation': 'collect_issue_types', 'jira_domain': jira_domain}
        )

        # Chama a tarefa Celery para coletar tipos de issues, passando o ID da task
        collect_issue_types.delay(jira_domain, jira_email, jira_api_token, task.id)
        
        return Response({"status": "Issue types collection started", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

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