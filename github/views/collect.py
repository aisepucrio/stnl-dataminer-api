import logging

from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.test import APIClient

from jobs.models import Task
from ..tasks import (
    fetch_commits,
    fetch_issues,
    fetch_pull_requests,
    fetch_branches,
    fetch_metadata
)
from ..serializers import GitHubCollectAllSerializer
from ..utils import DateTimeHandler

logger = logging.getLogger(__name__)


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
        
        # Task.objects.create(
        #     task_id=task.id,
        #     operation='fetch_commits',
        #     repository=repo_name,
        #     status='PENDING'
        # )

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
        
        # Task.objects.create(
        #     task_id=task.id,
        #     operation='fetch_issues',
        #     repository=repo_name,
        #     status='PENDING'
        # )

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
        
        # Task.objects.create(
        #     task_id=task.id,
        #     operation='fetch_pull_requests',
        #     repository=repo_name,
        #     status='PENDING'
        # )

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
        
        # Task.objects.create(
        #     task_id=task.id,
        #     operation='fetch_branches',
        #     repository=repo_name,
        #     status='PENDING'
        # )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)


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
        
        # Task.objects.create(
        #     task_id=task.id,
        #     operation='fetch_metadata',
        #     repository=repo_name,
        #     status='PENDING'
        # )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)


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

        if data_type == 'issue':
            task = fetch_issues.apply_async(args=[repo_name, start_date, end_date, depth])
        else:
            task = fetch_pull_requests.apply_async(args=[repo_name, start_date, end_date, depth])

        # Save the task in the database
        Task.objects.create(
            task_id=task.id,
            operation=f'fetch_{data_type}s',
            repository=repo_name,
            status='PENDING'
        )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)


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

        task = fetch_commits.apply_async(args=[repo_name, None, None, commit_sha])
        
        # Task.objects.create(
        #     task_id=task.id,
        #     operation='fetch_commits_by_sha',
        #     repository=repo_name,
        #     status='PENDING'
        # )

        return Response({
            "task_id": task.id,
            "message": "Task successfully initiated",
            "status_endpoint": f"http://localhost:8000/api/jobs/tasks/{task.id}/"
        }, status=status.HTTP_202_ACCEPTED)


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
                    logger.error(f"Error processing repository {repo_name}: {str(e)}")
                    repo_results['error'] = str(e)

                results.append(repo_results)

            return Response({
                'message': 'Mining tasks successfully initiated',
                'results': results
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Error in collect-all view: {str(e)}")
            return Response({
                'error': str(e),
                'detail': 'Internal error processing request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 