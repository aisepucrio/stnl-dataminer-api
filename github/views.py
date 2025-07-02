import json
import logging

from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.http import HttpResponse
from django.urls import reverse

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from rest_framework import generics, status, viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from jobs.models import Task
from .tasks import (
    fetch_commits,
    fetch_issues,
    fetch_pull_requests,
    fetch_branches,
    fetch_metadata
)
from .models import GitHubCommit, GitHubBranch, GitHubMetadata, GitHubIssuePullRequest, GitHubAuthor
from .serializers import (
    GitHubCommitSerializer,
    GitHubBranchSerializer,
    GitHubMetadataSerializer,
    GitHubIssuePullRequestSerializer,
    GraphDashboardSerializer,
    GitHubCollectAllSerializer,
    ExportDataSerializer,
    GitHubAuthorSerializer
)
from .utils import DateTimeHandler
from utils.lookup import get_filterset_fields as _get_filterset_fields, get_search_fields as _get_search_fields

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

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

        try:
            if start_date:
                start_date = DateTimeHandler.parse_date(start_date)
            if end_date:
                end_date = DateTimeHandler.parse_date(end_date)
            if start_date and end_date:
                DateTimeHandler.validate_date_range(start_date, end_date)
        except ValueError as e:
            return Response(
                {"error": str(e)},
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

        try:
            if start_date:
                start_date = DateTimeHandler.parse_date(start_date)
            if end_date:
                end_date = DateTimeHandler.parse_date(end_date)
            if start_date and end_date:
                DateTimeHandler.validate_date_range(start_date, end_date)
        except ValueError as e:
            return Response(
                {"error": str(e)},
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

        try:
            if start_date:
                start_date = DateTimeHandler.parse_date(start_date)
            if end_date:
                end_date = DateTimeHandler.parse_date(end_date)
            if start_date and end_date:
                DateTimeHandler.validate_date_range(start_date, end_date)
        except ValueError as e:
            return Response(
                {"error": str(e)},
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

@extend_schema(tags=["GitHub"], summary="List all GitHub commits")
class CommitListView(generics.ListAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubCommit)
    search_fields = _get_search_fields(GitHubCommit)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub commit")
class CommitDetailView(generics.RetrieveAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    lookup_field = 'sha'

@extend_schema(tags=["GitHub"], summary="List all GitHub issues")
class IssueListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubIssuePullRequest)
    search_fields = _get_search_fields(GitHubIssuePullRequest)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub issue")
class IssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

@extend_schema(tags=["GitHub"], summary="List all GitHub pull requests")
class PullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubIssuePullRequest)
    search_fields = _get_search_fields(GitHubIssuePullRequest)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination

@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub pull request")
class PullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

@extend_schema(tags=["GitHub"], summary="List all GitHub branches")
class BranchListView(generics.ListAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubBranch)
    search_fields = _get_search_fields(GitHubBranch)
    pagination_class = StandardResultsSetPagination
    ordering_fields = '__all__'

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
        
        # Save tasks
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
    filterset_fields = _get_filterset_fields(GitHubMetadata)
    search_fields = _get_search_fields(GitHubMetadata)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination

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
                    "data_type": {"type": "string", "description": "Type of data to fetch (issue or pull_request)", "default": "issue"},
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
        data_type = request.data.get('data_type', 'issue')
        depth = request.data.get('depth', 'basic')

        if not repo_name:
            return Response(
                {"error": "repo_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        task = fetch_issues_or_pull_requests.apply_async(args=[repo_name, start_date, end_date, data_type, depth])

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)

class IssuePullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.all()
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubIssuePullRequest)
    search_fields = _get_search_fields(GitHubIssuePullRequest)
    ordering_fields = _get_filterset_fields(GitHubIssuePullRequest)
    pagination_class = StandardResultsSetPagination

class IssuePullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.all()
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'

class UserListView(generics.ListAPIView):
    queryset = GitHubAuthor.objects.all()
    serializer_class = GitHubAuthorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubAuthor)
    search_fields = _get_search_fields(GitHubAuthor)
    ordering_fields = "__all__"
    pagination_class = StandardResultsSetPagination

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
    description="Provides statistics about repositories, issues, pull requests, commits, and unique commit users. "
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
                },
                "users_count": {"type": "integer", "description": "Number of unique commit users"}
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
                "time_mined": "2024-01-01T12:00:00Z",
                "users_count": 10
            },
            summary="Example with repository_id"
        ),
        OpenApiExample(
            "All Repositories Example with Date Filters",
            value={
                "issues_count": 500,
                "pull_requests_count": 200,
                "commits_count": 2000,
                "repositories_count": 5,
                "repositories": [
                    {"id": 1, "repository": "owner/repo1"},
                    {"id": 2, "repository": "owner/repo2"},
                    {"id": 3, "repository": "owner/repo3"},
                    {"id": 4, "repository": "owner/repo4"},
                    {"id": 5, "repository": "owner/repo5"}
                ],
                "users_count": 25
            },
            summary="Example without repository_id showing multiple repositories"
        ),
        OpenApiExample(
            "Repository Example with No Activity",
            value={
                "repository_id": 3,
                "repository_name": "owner/inactive-repo",
                "issues_count": 0,
                "pull_requests_count": 0,
                "commits_count": 0,
                "forks_count": 0,
                "stars_count": 0,
                "watchers_count": 0,
                "time_mined": "2024-01-01T12:00:00Z",
                "users_count": 0
            },
            summary="Example of repository with no activity"
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
        
        try:
            if start_date:
                start_date = DateTimeHandler.parse_date(start_date)
            if end_date:
                end_date = DateTimeHandler.parse_date(end_date)
            if start_date and end_date:
                DateTimeHandler.validate_date_range(start_date, end_date)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        issue_filters = {'data_type': 'issue'}
        pr_filters = {'data_type': 'pull_request'}
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
                    "time_mined": DateTimeHandler.format_date(metadata.time_mined),
                    "users_count": commits_query.values('author').distinct().count(),
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
                "repositories": list(repositories),
                "users_count": commits_query.values('author').distinct().count(),
            }
        
        return Response(response_data)

class GitHubCollectAllViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Mine selected data from multiple repositories",
        tags=["GitHub"],
        description="Endpoint to mine specific data from multiple repositories simultaneously",
        request=GitHubCollectAllSerializer,
        responses={
            202: OpenApiResponse(description="Tasks successfully initiated"),
            400: OpenApiResponse(description="Bad request - missing or invalid parameters")
        }
    )
    def create(self, request):
        try:
            serializer = GitHubCollectAllSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            repositories = serializer.validated_data['repositories']
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            depth = serializer.validated_data.get('depth', 'basic')
            collect_types = serializer.validated_data.get('collect_types')

            results = []
            client = APIClient()

            for repo_name in repositories:
                repo_results = {
                    'repository': repo_name,
                    'tasks': []
                }

                try:
                    if 'commits' in collect_types:
                        response = client.post(
                            reverse('github:commit-collect-list'),
                            {'repo_name': repo_name, 'start_date': start_date, 'end_date': end_date},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'commits',
                                'task_id': response.json().get('task_id')
                            })

                    if 'issues' in collect_types:
                        response = client.post(
                            reverse('github:issue-collect-list'),
                            {'repo_name': repo_name, 'start_date': start_date, 'end_date': end_date, 'depth': depth},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'issues',
                                'task_id': response.json().get('task_id')
                            })

                    if 'pull_requests' in collect_types:
                        response = client.post(
                            reverse('github:pullrequest-collect-list'),
                            {'repo_name': repo_name, 'start_date': start_date, 'end_date': end_date, 'depth': depth},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'pull_requests',
                                'task_id': response.json().get('task_id')
                            })

                    if 'branches' in collect_types:
                        response = client.post(
                            reverse('github:branch-collect-list'),
                            {'repo_name': repo_name},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'branches',
                                'task_id': response.json().get('task_id')
                            })

                    if 'metadata' in collect_types:
                        response = client.post(
                            reverse('github:metadata-collect-list'),
                            {'repo_name': repo_name},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'metadata',
                                'task_id': response.json().get('task_id')
                            })

                    if 'comments' in collect_types:
                        response = client.post(
                            reverse('github:issue-collect-list'),
                            {'repo_name': repo_name, 'start_date': start_date, 'end_date': end_date, 'depth': 'complex'},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'issues_with_comments',
                                'task_id': response.json().get('task_id')
                            })

                        response = client.post(
                            reverse('github:pullrequest-collect-list'),
                            {'repo_name': repo_name, 'start_date': start_date, 'end_date': end_date, 'depth': 'complex'},
                            format='json'
                        )
                        if response.status_code == 202:
                            repo_results['tasks'].append({
                                'type': 'pull_requests_with_comments',
                                'task_id': response.json().get('task_id')
                            })

                except Exception as e:
                    print(f"Error processing repository {repo_name}: {str(e)}")
                    repo_results['error'] = str(e)

                results.append(repo_results)

            return Response({
                'message': 'Mining tasks successfully initiated',
                'results': results
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            print(f"Error in collect-all view: {str(e)}")
            return Response({
                'error': str(e),
                'detail': 'Internal error processing request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(
    tags=["GitHub"],
    summary="Graph Dashboard",
    description="Provides cumulative time-series data for issues, pull requests, and commits over time. "
                "Can be filtered by repository_id, start_date, and end_date.",
    parameters=[
        OpenApiParameter(
            name="repository_id",
            description="ID of the repository to get statistics for. If not provided, returns aggregated stats for all repositories.",
            required=False,
            type=int
        ),
        OpenApiParameter(
            name="start_date",
            description="Filter display window from this date onwards (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME
        ),
        OpenApiParameter(
            name="end_date",
            description="Filter display window up to this date (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME
        ),
        OpenApiParameter(
            name="interval",
            description="Time interval for grouping data (day, week, month). Default is 'day'.",
            required=False,
            type=str,
            default="day"
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "repository_id": {"type": "integer", "nullable": True},
                "repository_name": {"type": "string", "nullable": True},
                "time_series": {
                    "type": "object",
                    "properties": {
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "issues": {"type": "array", "items": {"type": "integer"}},
                        "pull_requests": {"type": "array", "items": {"type": "integer"}},
                        "commits": {"type": "array", "items": {"type": "integer"}}
                    }
                }
            }
        },
        400: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            },
            "description": "Bad request due to invalid parameters"
        }
    },
    examples=[
        OpenApiExample(
            "Single Repository Example",
            value={
                "repository_id": 1,
                "repository_name": "owner/repo",
                "time_series": {
                    "labels": ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "issues": [5, 8, 15],
                    "pull_requests": [2, 6, 7],
                    "commits": [10, 18, 30]
                }
            },
            description="Example response for a specific repository showing cumulative counts"
        ),
        OpenApiExample(
            "All Repositories Example",
            value={
                "time_series": {
                    "labels": ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "issues": [15, 27, 47],
                    "pull_requests": [8, 18, 23],
                    "commits": [25, 55, 83]
                }
            },
            description="Example response for all repositories showing cumulative counts"
        ),
        OpenApiExample(
            "Monthly Interval Example",
            value={
                "repository_id": 1,
                "repository_name": "owner/repo",
                "time_series": {
                    "labels": ["2024-01", "2024-02", "2024-03"],
                    "issues": [50, 95, 155],
                    "pull_requests": [20, 45, 63],
                    "commits": [100, 195, 305]
                }
            },
            description="Example response with monthly interval showing cumulative counts"
        )
    ]
)
class GraphDashboardView(APIView):
    def get(self, request):
        # Validate request parameters using serializer
        serializer = GraphDashboardSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        validated_data = serializer.validated_data
        repository_id = validated_data.get('repository_id')
        start_date = validated_data.get('start_date')
        end_date = validated_data.get('end_date')
        interval = validated_data.get('interval', 'day')
        
        # Set up date truncation based on interval
        if interval == 'day':
            trunc_func = TruncDay
            date_format = '%Y-%m-%d'
        elif interval == 'month':
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        else:
            trunc_func = TruncYear
            date_format = '%Y'
        
        # Base querysets - get all data from the database
        issues_query = GitHubIssuePullRequest.objects.filter(data_type='issue')
        prs_query = GitHubIssuePullRequest.objects.filter(data_type='pull_request')
        commits_query = GitHubCommit.objects.all()
        
        # Apply repository filter if provided
        repository_name = None
        if repository_id:
            try:
                metadata = GitHubMetadata.objects.get(id=repository_id)
                repository_name = metadata.repository
                
                issues_query = issues_query.filter(repository=repository_name)
                prs_query = prs_query.filter(repository=repository_name)
                commits_query = commits_query.filter(repository=repository_name)
            except GitHubMetadata.DoesNotExist:
                pass

        # Get all data up to end_date for cumulative counts
        if end_date:
            issues_query = issues_query.filter(created_at__lte=end_date)
            prs_query = prs_query.filter(created_at__lte=end_date)
            commits_query = commits_query.filter(date__lte=end_date)
        
        # Group data by date interval and calculate cumulative counts
        issues_by_date = issues_query.annotate(
            interval=trunc_func('created_at')
        ).values('interval').annotate(count=Count('id')).order_by('interval')
        
        prs_by_date = prs_query.annotate(
            interval=trunc_func('created_at')
        ).values('interval').annotate(count=Count('id')).order_by('interval')
        
        commits_by_date = commits_query.annotate(
            interval=trunc_func('date')
        ).values('interval').annotate(count=Count('id')).order_by('interval')
        
        # Convert to dictionaries with cumulative counts
        issues_dict = {}
        prs_dict = {}
        commits_dict = {}
        
        cumulative_issues = 0
        cumulative_prs = 0
        cumulative_commits = 0
        
        for item in issues_by_date:
            cumulative_issues += item['count']
            issues_dict[item['interval'].strftime(date_format)] = cumulative_issues
            
        for item in prs_by_date:
            cumulative_prs += item['count']
            prs_dict[item['interval'].strftime(date_format)] = cumulative_prs
            
        for item in commits_by_date:
            cumulative_commits += item['count']
            commits_dict[item['interval'].strftime(date_format)] = cumulative_commits
        
        # Get all unique dates
        all_dates = set()
        for date_dict in [issues_dict, prs_dict, commits_dict]:
            all_dates.update(date_dict.keys())
        
        # Filter date range if start_date is provided
        date_range = sorted(list(all_dates))
        if start_date:
            date_range = [d for d in date_range if d >= start_date.strftime(date_format)]
        
        # Fill in the cumulative data for each date in the range
        # Use the last known cumulative value for dates with no new items
        issues_data = []
        prs_data = []
        commits_data = []
        
        last_issues = 0
        last_prs = 0
        last_commits = 0
        
        for date_str in date_range:
            last_issues = issues_dict.get(date_str, last_issues)
            last_prs = prs_dict.get(date_str, last_prs)
            last_commits = commits_dict.get(date_str, last_commits)
            
            issues_data.append(last_issues)
            prs_data.append(last_prs)
            commits_data.append(last_commits)
        
        # Prepare response
        response_data = {
            "time_series": {
                "labels": date_range,
                "issues": issues_data,
                "pull_requests": prs_data,
                "commits": commits_data
            }
        }
        
        if repository_id:
            response_data["repository_id"] = repository_id
            response_data["repository_name"] = repository_name
        
        return Response(response_data)

class ExportDataView(APIView):
    @extend_schema(
        summary="Export GitHub data",
        tags=["GitHub"],
        description="Export data from GitHub tables. For githubissuepullrequest table, you can filter by data_type (issue/pull_request).",
        request=ExportDataSerializer,
        responses={
            200: OpenApiResponse(description="Exported data file"),
            400: OpenApiResponse(description="Invalid parameters"),
            404: OpenApiResponse(description="Table not found or no data found"),
            500: OpenApiResponse(description="Server error")
        },
        examples=[
            OpenApiExample(
                "Export all issues and pull requests",
                value={
                    "table": "githubissuepullrequest",
                    "format": "json"
                },
                summary="Export all data from githubissuepullrequest table"
            ),
            OpenApiExample(
                "Export only issues",
                value={
                    "table": "githubissuepullrequest",
                    "data_type": "issue",
                    "format": "json"
                },
                summary="Export only issues from githubissuepullrequest table"
            ),
            OpenApiExample(
                "Export only pull requests",
                value={
                    "table": "githubissuepullrequest",
                    "data_type": "pull_request",
                    "format": "json"
                },
                summary="Export only pull requests from githubissuepullrequest table"
            ),
            OpenApiExample(
                "Export specific commits by IDs",
                value={
                    "table": "githubcommit",
                    "ids": [1, 2, 3],
                    "format": "json"
                },
                summary="Export specific commits by their IDs"
            )
        ]
    )
    def post(self, request):
        serializer = ExportDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        table = serializer.validated_data['table']
        ids = serializer.validated_data.get('ids', [])
        format_type = serializer.validated_data['format']
        data_type = serializer.validated_data.get('data_type')

        model_mapping = {
            'githubcommit': GitHubCommit,
            'githubbranch': GitHubBranch,
            'githubmetadata': GitHubMetadata,
            'githubissuepullrequest': GitHubIssuePullRequest
        }

        if table not in model_mapping:
            return Response(
                {"error": f"Table '{table}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        model = model_mapping[table]
        queryset = model.objects.all()

        if table == 'githubissuepullrequest':
            if data_type:
                queryset = queryset.filter(data_type=data_type)

        if ids:
            queryset = queryset.filter(id__in=ids)

        data = []
        for obj in queryset:
            obj_dict = {}
            for field in obj._meta.fields:
                value = getattr(obj, field.name)
                if hasattr(value, 'id'):
                    obj_dict[field.name] = value.id
                else:
                    obj_dict[field.name] = value
            data.append(obj_dict)

        if not data:
            return Response(
                {"error": "No data found to export"},
                status=status.HTTP_404_NOT_FOUND
            )

        filename_parts = [table]
        if table == 'githubissuepullrequest':
            if data_type:
                filename_parts.append(data_type)
        filename = f"{'_'.join(filename_parts)}_export.json"

        try:
            response = HttpResponse(
                json.dumps(data, default=str, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'

            return response

        except Exception as e:
            return Response(
                {"error": f"Error exporting data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )