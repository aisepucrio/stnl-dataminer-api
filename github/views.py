from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from jobs.tasks import fetch_commits, fetch_issues, fetch_pull_requests, fetch_branches
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch
from .serializers import GitHubCommitSerializer, GitHubIssueSerializer, GitHubPullRequestSerializer, GitHubBranchSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import GitHubCommitFilter, GitHubIssueFilter, GitHubPullRequestFilter, GitHubBranchFilter

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
            "task_id": task.id,
            "message": "Task successfully initiated",
            "instructions": "To check the task status, make a GET request to: "
                          f"http://localhost:8000/jobs/{task.id}/",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_200_OK)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_pull_requests.apply_async(args=[repo_name, start_date, end_date])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "instructions": "To check the task status, make a GET request to: "
                          f"http://localhost:8000/jobs/{task.id}/",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_200_OK)

class GitHubBranchViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')

        task = fetch_branches.apply_async(args=[repo_name])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "instructions": "To check the task status, make a GET request to: "
                          f"http://localhost:8000/jobs/{task.id}/",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_200_OK)

# Novas views genéricas para consulta
class CommitListView(generics.ListAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubCommitFilter
    search_fields = ['message', 'author__name']
    ordering_fields = ['date']

class CommitDetailView(generics.RetrieveAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    lookup_field = 'sha'

class IssueListView(generics.ListAPIView):
    queryset = GitHubIssue.objects.all()
    serializer_class = GitHubIssueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubIssueFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

class IssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssue.objects.all()
    serializer_class = GitHubIssueSerializer
    lookup_field = 'issue_id'

class PullRequestListView(generics.ListAPIView):
    queryset = GitHubPullRequest.objects.all()
    serializer_class = GitHubPullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubPullRequestFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

class PullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubPullRequest.objects.all()
    serializer_class = GitHubPullRequestSerializer
    lookup_field = 'pr_id'

class BranchListView(generics.ListAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GitHubBranchFilter

class BranchDetailView(generics.RetrieveAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    lookup_field = 'name'
