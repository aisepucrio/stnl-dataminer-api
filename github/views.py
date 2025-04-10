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
from rest_framework.views import APIView
from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

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


@extend_schema(
    summary="Dashboard statistics",
    description="Provides statistics about repositories, issues, pull requests, and commits. "
                "If repository_id is provided, returns detailed stats for that repository.",
    parameters=[
        OpenApiParameter(
            name="repository_id",
            description="ID of the repository to get statistics for. If not provided, returns aggregated stats for all repositories.",
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
                "repository_id": {"type": "integer", "nullable": True},
                "repository_name": {"type": "string", "nullable": True},
                "issues_count": {"type": "integer"},
                "pull_requests_count": {"type": "integer"},
                "commits_count": {"type": "integer"},
                "forks_count": {"type": "integer", "nullable": True},
                "stars_count": {"type": "integer", "nullable": True},
                "watchers_count": {"type": "integer", "nullable": True},
                "time_mined": {"type": "string", "format": "date-time", "nullable": True},
                "repositories_count": {"type": "integer", "nullable": True},
                "repositories": {
                    "type": "array", 
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "repository": {"type": "string"}
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
            "Repository Example",
            value={
                "repository_id": 1,
                "repository_name": "owner/repo",
                "issues_count": 120,
                "pull_requests_count": 45,
                "commits_count": 500,
                "forks_count": 25,
                "stars_count": 100,
                "watchers_count": 30,
                "time_mined": "2023-01-01T12:00:00Z"
            },
            summary="Example with repository_id"
        ),
        OpenApiExample(
            "All Repositories Example",
            value={
                "issues_count": 500,
                "pull_requests_count": 200,
                "commits_count": 2000,
                "repositories_count": 5,
                "repositories": [
                    {"id": 1, "repository": "owner/repo1"},
                    {"id": 2, "repository": "owner/repo2"}
                ]
            },
            summary="Example without repository_id"
        )
    ]
)
class DashboardView(APIView):
    def get(self, request):
        # Get query parameters
        repository_id = request.query_params.get('repository_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Set default dates if not provided
        if not start_date:
            start_date = "1970-01-01T00:00:00Z"  # Beginning of time for practical purposes
        
        if not end_date:
            end_date = timezone.now().isoformat()
        
        # Filter by date range
        issues_query = GitHubIssuePullRequest.objects.filter(
            tipo='issue',
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        prs_query = GitHubIssuePullRequest.objects.filter(
            tipo='pull_request',
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        commits_query = GitHubCommit.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        # If repository_id is specified, filter by repository
        if repository_id:
            try:
                # Get repository metadata by ID
                metadata = GitHubMetadata.objects.get(id=repository_id)
                repository_name = metadata.repository
                
                # Filter queries by repository name
                issues_query = issues_query.filter(repository=repository_name)
                prs_query = prs_query.filter(repository=repository_name)
                commits_query = commits_query.filter(repository=repository_name)
                
                response_data = {
                    "repository_id": repository_id,
                    "repository_name": repository_name,
                    "issues_count": issues_query.count(),
                    "pull_requests_count": prs_query.count(),
                    "commits_count": commits_query.count(),
                    "forks_count": metadata.forks_count,
                    "stars_count": metadata.stars_count,
                    "watchers_count": metadata.watchers_count,
                    "time_mined": metadata.time_mined
                }
            except GitHubMetadata.DoesNotExist:
                # If metadata doesn't exist, return error
                return Response(
                    {"error": f"Repository with ID {repository_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Aggregate data for all repositories
            repositories = GitHubMetadata.objects.values('id', 'repository')
            
            response_data = {
                "issues_count": issues_query.count(),
                "pull_requests_count": prs_query.count(),
                "commits_count": commits_query.count(),
                "repositories_count": repositories.count(),
                "repositories": list(repositories)
            }
        
        return Response(response_data)
