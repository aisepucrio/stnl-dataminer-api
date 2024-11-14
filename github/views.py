from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from jobs.tasks import fetch_commits, fetch_issues, fetch_pull_requests, fetch_branches

class GitHubCommitViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Inicia a tarefa e aguarda o resultado
        task = fetch_commits.apply_async(args=[repo_name, start_date, end_date])
        result = AsyncResult(task.id)
        data = result.get()  # Aguarda o término da tarefa para obter os dados minerados

        return Response(data, status=status.HTTP_200_OK)

class GitHubIssueViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_issues.apply_async(args=[repo_name, start_date, end_date])
        result = AsyncResult(task.id)
        data = result.get()

        return Response(data, status=status.HTTP_200_OK)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        task = fetch_pull_requests.apply_async(args=[repo_name, start_date, end_date])
        result = AsyncResult(task.id)
        data = result.get()

        return Response(data, status=status.HTTP_200_OK)

class GitHubBranchViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')

        task = fetch_branches.apply_async(args=[repo_name])
        result = AsyncResult(task.id)
        data = result.get()

        return Response(data, status=status.HTTP_200_OK)
