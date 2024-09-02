from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import JiraIssueType, JiraIssue
from .serializers import JiraIssueSerializer
from .tasks import fetch_issue_types, collect_jira_issues

class FetchIssueTypesView(APIView):
    def post(self, request, *args, **kwargs):
        jira_domain = request.data.get('jira_domain')
        project_key = request.data.get('project_key')
        jira_email = request.data.get('jira_email')
        jira_api_token = request.data.get('jira_api_token')
        
        if not all([jira_domain, project_key, jira_email, jira_api_token]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        result = fetch_issue_types(jira_domain, project_key, jira_email, jira_api_token)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        issue_types = JiraIssueType.objects.filter(domain=jira_domain, project_key=project_key)
        serialized_issue_types = [{"id": it.issue_type_id, "name": it.issue_type_name} for it in issue_types]

        return Response({"issue_types": serialized_issue_types}, status=status.HTTP_200_OK)


class JiraIssueCollectView(APIView):
    def post(self, request, *args, **kwargs):
        jira_domain = request.data.get('jira_domain')
        project_key = request.data.get('project_key')
        jira_email = request.data.get('jira_email')
        jira_api_token = request.data.get('jira_api_token')
        issuetypes = request.data.get('issuetypes', [])
        start_date = request.data.get('start_date', None)  # Data de início (opcional)
        end_date = request.data.get('end_date', None)  # Data de fim (opcional)
        
        
        if not all([project_key, jira_domain, jira_email, jira_api_token, issuetypes, start_date, end_date]):
            return Response({"error": "All fields are required, including issue_types"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Chama a tarefa Celery para minerar issues
        collect_jira_issues.delay(jira_domain, project_key, jira_email, jira_api_token, issuetypes)
        
        return Response({"status": "Issue collection started"}, status=status.HTTP_202_ACCEPTED)

class IssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer

class IssueDetailView(generics.RetrieveAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    lookup_field = 'id'

class IssueDeleteView(generics.DestroyAPIView):
    queryset = JiraIssue.objects.all()
    lookup_field = 'id'
    
    def delete(self, request, *args, **kwargs):
        issue = self.get_object()
        self.perform_destroy(issue)
        return Response({"status": "Issue deleted successfully"}, status=status.HTTP_204_NO_CONTENT)