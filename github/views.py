from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from jobs.tasks import fetch_commits, fetch_issues, fetch_pull_requests, fetch_branches, fetch_metadata
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubMetadata, GitHubIssuePullRequest
from .serializers import GitHubCommitSerializer, GitHubIssueSerializer, GitHubPullRequestSerializer, GitHubBranchSerializer, GitHubMetadataSerializer, GitHubIssuePullRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import GitHubCommitFilter, GitHubIssueFilter, GitHubPullRequestFilter, GitHubBranchFilter, GitHubIssuePullRequestFilter

class GitHubCommitViewSet(viewsets.ViewSet):
    def create(self, request):
        """
        Endpoint para minerar commits de um repositório.
        Aceita POST com parâmetros no body:
        {
            "repo_name": "owner/repo",
            "start_date": "2024-01-01T00:00:00Z",  # opcional
            "end_date": "2024-03-01T00:00:00Z"     # opcional
        }
        """
        repo_name = request.data.get('repo_name')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_commits.apply_async(args=[repo_name, start_date, end_date])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class GitHubIssueViewSet(viewsets.ViewSet):
    def create(self, request):
        repo_name = request.data.get('repo_name')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        depth = request.data.get('depth', 'basic')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_issues.apply_async(args=[repo_name, start_date, end_date, depth])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    def create(self, request):
        repo_name = request.data.get('repo_name')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        depth = request.data.get('depth', 'basic')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_pull_requests.apply_async(args=[repo_name, start_date, end_date, depth])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class GitHubBranchViewSet(viewsets.ViewSet):
    def create(self, request):
        repo_name = request.data.get('repo_name')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_branches.apply_async(args=[repo_name])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

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
    queryset = GitHubIssuePullRequest.objects.filter(tipo='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubIssuePullRequestFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

class IssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

class PullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubIssuePullRequestFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

class PullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

class BranchListView(generics.ListAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GitHubBranchFilter

class BranchDetailView(generics.RetrieveAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    lookup_field = 'name'

class GitHubMetadataViewSet(viewsets.ViewSet):
    def create(self, request):
        repo_name = request.data.get('repo_name')
        
        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_metadata.apply_async(args=[repo_name])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class MetadataListView(generics.ListAPIView):
    queryset = GitHubMetadata.objects.all()
    serializer_class = GitHubMetadataSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['repository', 'language']
    ordering_fields = ['stars_count', 'forks_count', 'created_at', 'updated_at']

class GitHubIssuePullRequestViewSet(viewsets.ViewSet):
    def create(self, request):
        repo_name = request.data.get('repo_name')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        tipo = request.data.get('tipo', 'issue')
        depth = request.data.get('depth', 'basic')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_issues_or_pull_requests.apply_async(args=[repo_name, start_date, end_date, tipo, depth])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/jobs/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class IssuePullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.all()
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubIssuePullRequestFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

class IssuePullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.all()
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'
