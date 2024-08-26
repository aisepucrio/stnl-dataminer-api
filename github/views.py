# github/views.py

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from jobs.tasks import fetch_commits, fetch_issues, fetch_pull_requests, fetch_branches

class GitHubCommitViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_commits.delay(repo_name, start_date, end_date)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

class GitHubIssueViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_issues.delay(repo_name, start_date, end_date)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_pull_requests.delay(repo_name, start_date, end_date)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

class GitHubBranchViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')

        task = fetch_branches.delay(repo_name)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)
