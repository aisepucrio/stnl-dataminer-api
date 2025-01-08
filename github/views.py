from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from jobs.tasks import fetch_commits, fetch_issues, fetch_pull_requests, fetch_branches
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch
from .serializers import GitHubCommitSerializer, GitHubIssueSerializer, GitHubPullRequestSerializer, GitHubBranchSerializer

class GitHubCommitViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Inicia a tarefa e obtém o ID da tarefa
        task = fetch_commits.apply_async(args=[repo_name, start_date, end_date]) 

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "instructions": "To check the task status, make a GET request to: "
                          f"http://localhost:8000/jobs/{task.id}/",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_200_OK)

class GitHubIssueViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_issues.apply_async(args=[repo_name, start_date, end_date])

        return Response({
            "task_id": task.id
        }, status=status.HTTP_200_OK)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_pull_requests.apply_async(args=[repo_name, start_date, end_date])

        return Response({
            "task_id": task.id
        }, status=status.HTTP_200_OK)

class GitHubBranchViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')

        task = fetch_branches.apply_async(args=[repo_name])

        return Response({
            "task_id": task.id
        }, status=status.HTTP_200_OK)

# Novas views genéricas para consulta
class CommitListView(generics.ListAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    filterset_fields = ['repository', 'author', 'date']

class CommitDetailView(generics.RetrieveAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    lookup_field = 'sha'

class IssueListView(generics.ListAPIView):
    queryset = GitHubIssue.objects.all()
    serializer_class = GitHubIssueSerializer
    filterset_fields = ['repository', 'state', 'creator']

class IssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssue.objects.all()
    serializer_class = GitHubIssueSerializer
    lookup_field = 'issue_id'

class PullRequestListView(generics.ListAPIView):
    queryset = GitHubPullRequest.objects.all()
    serializer_class = GitHubPullRequestSerializer
    filterset_fields = ['repository', 'state', 'creator']

class PullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubPullRequest.objects.all()
    serializer_class = GitHubPullRequestSerializer
    lookup_field = 'pr_id'

class BranchListView(generics.ListAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    filterset_fields = ['repository', 'name']

class BranchDetailView(generics.RetrieveAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    lookup_field = 'name'
