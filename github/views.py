from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework import status
from jobs.tasks import fetch_commits, fetch_issues, fetch_pull_requests, fetch_branches, fetch_metadata
from .models import GitHubCommit, GitHubBranch, GitHubMetadata, GitHubIssuePullRequest
from .serializers import GitHubCommitSerializer, GitHubBranchSerializer, GitHubMetadataSerializer, GitHubIssuePullRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import GitHubCommitFilter, GitHubBranchFilter, GitHubIssuePullRequestFilter
from rest_framework.views import APIView
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .filters import GitHubCommitFilter, GitHubBranchFilter, GitHubIssuePullRequestFilter
from jobs.models import Task

class GitHubCommitViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine GitHub commits",
        tags=["GitHub"],
        description="Endpoint to mine commits from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"},
                    "start_date": {"type": "string", "format": "date-time", "description": "Start date in ISO format (optional)"},
                    "end_date": {"type": "string", "format": "date-time", "description": "End date in ISO format (optional)"}
                },
                "required": ["repo_name"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
    def create(self, request):
        repo_name = request.data.get('repo_name')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        commit_sha = request.data.get('commit_sha')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_commits.apply_async(args=[repo_name, start_date, end_date, commit_sha])
        
        # Save the task in the database
        Task.objects.create(
            task_id=task.id,
            operation='fetch_commits',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class GitHubIssueViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine GitHub issues",
        tags=["GitHub"],
        description="Endpoint to mine issues from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"},
                    "start_date": {"type": "string", "format": "date-time", "description": "Start date in ISO format (optional)"},
                    "end_date": {"type": "string", "format": "date-time", "description": "End date in ISO format (optional)"},
                    "depth": {"type": "string", "description": "Depth of data to fetch (basic or full)", "default": "basic"}
                },
                "required": ["repo_name"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
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
        
        # Save the task in the database
        Task.objects.create(
            task_id=task.id,
            operation='fetch_issues',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine GitHub pull requests",
        tags=["GitHub"],
        description="Endpoint to mine pull requests from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"},
                    "start_date": {"type": "string", "format": "date-time", "description": "Start date in ISO format (optional)"},
                    "end_date": {"type": "string", "format": "date-time", "description": "End date in ISO format (optional)"},
                    "depth": {"type": "string", "description": "Depth of data to fetch (basic or full)", "default": "basic"}
                },
                "required": ["repo_name"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
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
        
        # Save the task in the database
        Task.objects.create(
            task_id=task.id,
            operation='fetch_pull_requests',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class GitHubBranchViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine GitHub branches",
        tags=["GitHub"],
        description="Endpoint to mine branches from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"}
                },
                "required": ["repo_name"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
    def create(self, request):
        repo_name = request.data.get('repo_name')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_branches.apply_async(args=[repo_name])
        
        Task.objects.create(
            task_id=task.id,
            operation='fetch_branches',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

# Novas views genéricas para consulta
@extend_schema(tags=["GitHub"], summary="List all GitHub commits")
class CommitListView(generics.ListAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubCommitFilter
    search_fields = ['message', 'author__name']
    ordering_fields = ['date']

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub commit")
class CommitDetailView(generics.RetrieveAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    lookup_field = 'sha'

@extend_schema(tags=["GitHub"], summary="List all GitHub issues")
class IssueListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubIssuePullRequestFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub issue")
class IssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

@extend_schema(tags=["GitHub"], summary="List all GitHub pull requests")
class PullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GitHubIssuePullRequestFilter
    search_fields = ['title', 'creator']
    ordering_fields = ['created_at', 'updated_at']

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub pull request")
class PullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(tipo='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

@extend_schema(tags=["GitHub"], summary="List all GitHub branches")
class BranchListView(generics.ListAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GitHubBranchFilter

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub branch")
class BranchDetailView(generics.RetrieveAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    lookup_field = 'name'

class GitHubMetadataViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine GitHub repository metadata",
        tags=["GitHub"],
        description="Endpoint to mine metadata from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"}
                },
                "required": ["repo_name"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
    def create(self, request):
        repo_name = request.data.get('repo_name')
        
        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_metadata.apply_async(args=[repo_name])
        
        # Salva a task no banco de dados
        Task.objects.create(
            task_id=task.id,
            operation='fetch_metadata',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

@extend_schema(tags=["GitHub"], summary="List all GitHub repository metadata")
class MetadataListView(generics.ListAPIView):
    queryset = GitHubMetadata.objects.all()
    serializer_class = GitHubMetadataSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['repository', 'language']
    ordering_fields = ['stars_count', 'forks_count', 'created_at', 'updated_at']

class GitHubIssuePullRequestViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine GitHub issues or pull requests",
        tags=["GitHub"],
        description="Endpoint to mine issues or pull requests from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"},
                    "start_date": {"type": "string", "format": "date-time", "description": "Start date in ISO format (optional)"},
                    "end_date": {"type": "string", "format": "date-time", "description": "End date in ISO format (optional)"},
                    "tipo": {"type": "string", "description": "Type of data to fetch (issue or pull_request)", "default": "issue"},
                    "depth": {"type": "string", "description": "Depth of data to fetch (basic or full)", "default": "basic"}
                },
                "required": ["repo_name"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
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
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
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

class GitHubCommitByShaViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine a specific GitHub commit by SHA",
        tags=["GitHub"],
        description="Endpoint to mine a specific commit by its SHA hash from a repository",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format owner/repo"},
                    "commit_sha": {"type": "string", "description": "SHA hash of the commit to fetch"}
                },
                "required": ["repo_name", "commit_sha"]
            }
        },
        responses={
            202: OpenApiResponse(description="Task successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing required parameters")
        }
    )
    def create(self, request):
        repo_name = request.data.get('repo_name')
        commit_sha = request.data.get('commit_sha')

        if not repo_name or not commit_sha:
            return Response(
                {"error": "repo_name and commit_sha are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_commit_by_sha.apply_async(args=[repo_name, commit_sha])
        
        Task.objects.create(
            task_id=task.id,
            operation='fetch_commit_by_sha',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

@extend_schema(
    tags=["GitHub"],
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
            description="Filter data from this date onwards (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME
        ),
        OpenApiParameter(
            name="end_date",
            description="Filter data up to this date (ISO format).",
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
        400: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            },
            "description": "Bad request due to invalid parameters (repository_id not an integer, invalid date format, start_date after end_date)"
        },
        404: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            },
            "description": "Repository with specified ID not found"
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
        repository_id = request.query_params.get('repository_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if repository_id:
            try:
                repository_id = int(repository_id)
            except ValueError:
                return Response(
                    {"error": "repository_id must be an integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if start_date or end_date:
            try:
                if start_date:
                    start_datetime = timezone.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                
                if end_date:
                    end_datetime = timezone.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                
                if start_date and end_date and start_datetime > end_datetime:
                    return Response(
                        {"error": "start_date must be before end_date"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        issue_filters = {'tipo': 'issue'}
        pr_filters = {'tipo': 'pull_request'}
        commit_filters = {}
        
        if start_date:
            issue_filters['created_at__gte'] = start_date
            pr_filters['created_at__gte'] = start_date
            commit_filters['date__gte'] = start_date
            
        if end_date:
            issue_filters['created_at__lte'] = end_date
            pr_filters['created_at__lte'] = end_date
            commit_filters['date__lte'] = end_date
        
        issues_query = GitHubIssuePullRequest.objects.filter(**issue_filters)
        prs_query = GitHubIssuePullRequest.objects.filter(**pr_filters)
        commits_query = GitHubCommit.objects.filter(**commit_filters)
        
        if repository_id:
            try:
                metadata = GitHubMetadata.objects.get(id=repository_id)
                repository_name = metadata.repository
                
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
                return Response(
                    {"error": f"Repository with ID {repository_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            repositories = GitHubMetadata.objects.values('id', 'repository')
            
            response_data = {
                "issues_count": issues_query.count(),
                "pull_requests_count": prs_query.count(),
                "commits_count": commits_query.count(),
                "repositories_count": repositories.count(),
                "repositories": list(repositories)
            }
        
        return Response(response_data)
