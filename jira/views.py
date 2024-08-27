from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import JiraIssue
from .serializers import JiraIssueSerializer
from .tasks import collect_jira_issues

class JiraIssueCollectView(APIView):
    def post(self, request, *args, **kwargs):
        user_id= request.user.id
        project_key = request.data.get('project_key')
        jira_domain = request.data.get('jira_domain')
        
        if not project_key or not jira_domain:
            return Response({"error": "Project key and Jira domain are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Chama a tarefa Celery para minerar issues
        collect_jira_issues.delay(jira_domain, project_key)
        
        return Response({"status": "Issue collection started"}, status=status.HTTP_202_ACCEPTED)

class IssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer

class IssueDetailView(generics.RetrieveAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    lookup_field = 'id'

