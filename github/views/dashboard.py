import logging

from django.db.models import Count, Min, Max
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import GitHubCommit, GitHubMetadata, GitHubIssuePullRequest
from ..serializers import GraphDashboardSerializer
from ..utils import DateTimeHandler

logger = logging.getLogger(__name__)


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
                
                issues_query = issues_query.filter(repository=metadata)
                prs_query = prs_query.filter(repository=metadata)
                commits_query = commits_query.filter(repository=metadata)
                
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
                
                issues_query = issues_query.filter(repository=metadata)
                prs_query = prs_query.filter(repository=metadata)
                commits_query = commits_query.filter(repository=metadata)
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


@extend_schema(
    tags=["GitHub"],
    summary="Repository date range",
    description="Returns the earliest (min_date) and latest (max_date) commit dates for a given repository_id.",
    parameters=[
        OpenApiParameter(
            name="repository_id",
                description="Query parameter. ID of the repository to get date range for.",
            required=True,
            type=int
        ),
    ],
    responses={
        200: OpenApiResponse(response={"type": "object", "properties": {"repository_id": {"type": "integer"}, "min_date": {"type": "string", "format": "date-time", "nullable": True}, "max_date": {"type": "string", "format": "date-time", "nullable": True}}}),
        400: OpenApiResponse(response={"type": "object", "properties": {"error": {"type": "string"}}}),
        404: OpenApiResponse(response={"type": "object", "properties": {"error": {"type": "string"}}})
    }
)
class RepositoryDateRangeView(APIView):
    def get(self, request):
        # Accept repository_id via query parameter only
        repository_id = request.query_params.get('repository_id')

        if repository_id is None:
            return Response({"error": "repository_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            repository_id = int(repository_id)
        except (ValueError, TypeError):
            return Response({"error": "repository_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            metadata = GitHubMetadata.objects.get(id=repository_id)
        except GitHubMetadata.DoesNotExist:
            return Response({"error": f"Repository with ID {repository_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        # Compute min and max dates from commits for this repository
        commit_dates = GitHubCommit.objects.filter(repository=metadata).aggregate(
            min_date=Min('date'),
            max_date=Max('date')
        )

        # Format dates using DateTimeHandler if present
        min_date = commit_dates.get('min_date')
        max_date = commit_dates.get('max_date')

        response = {
            "repository_id": repository_id,
            "min_date": DateTimeHandler.format_date(min_date) if min_date else None,
            "max_date": DateTimeHandler.format_date(max_date) if max_date else None,
        }

        return Response(response)