from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from git import Repo, RemoteProgress, GitCommandError
from tqdm import tqdm
from pydriller import Repository as Repo
from fastapi import HTTPException
import os
import json
import requests

class CloneProgress(RemoteProgress):
    def __init__(self):
        super().__init__()
        self.pbar = tqdm()
    
    # Atualiza barra de progresso
    def update(self, op_code, cur_count, max_count=None, message=''):
        self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()

class GitHubMiner:
    def __init__(self):
        # Inicialização de tokens, cabeçalhos e outras variáveis
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        self.auth = None
        self.tokens = None
        self.usernames = None
        self.current_token_index = 0
        self.load_tokens()

    def load_tokens(self):
        # Função para carregar tokens de um arquivo .env
        pass

    def user_home_directory(self):
        return os.path.expanduser("~")

    def clone_repo(self, repo_url, clone_path):
        print(f'\nCloning repo: {repo_url}\n')
        Repo.clone_from(repo_url, clone_path, progress=CloneProgress())

    def update_repo(self, repo_path):
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f'\nRepo updated: {repo_path}\n')
        except GitCommandError as e:
            if 'CONFLICT' in str(e):
                print(f'Conflict detected: {e}')
                self.resolve_conflicts(repo)
            else:
                print(f'Error updating repo: {e}')

    def get_commits(self, repo_name: str, start_date: str = None, end_date: str = None, clone_path: str = None):
        try:
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%SZ')
            else:
                start_date = datetime.min

            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%SZ')
            else:
                end_date = datetime.now()

            clone_path = clone_path if clone_path is not None else os.path.join(self.user_home_directory(), 'GitHubClones')

            if not os.path.exists(clone_path):
                repo_url = f'https://github.com/{repo_name}'
                self.clone_repo(repo_url, clone_path)
                repo_path = os.path.join(clone_path, repo_name.split('/')[1])
            else:
                repo_path = os.path.join(clone_path, repo_name.split('/')[1])
                self.update_repo(repo_path)

            repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()

            essential_commits = []
            for commit in repo:
                commit_data = {
                    'sha': commit.hash,
                    'message': commit.msg,
                    'date': commit.author_date.isoformat(),
                    'author': {
                        'name': commit.author.name,
                        'email': commit.author.email
                    },
                    'lines': {
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files': commit.files
                    }
                }
                essential_commits.append(commit_data)

            return essential_commits

        except Exception as e:
            print(f"Erro ao acessar o repositório: {e}")
            return []

    def get_issues(self, repo_name, start_date, end_date):
        max_workers = int(self.get_max_workers())
        url = f'https://api.github.com/repos/{repo_name}/issues'
        params = {
            'since': f'{start_date}T00:00:01Z',
            'until': f'{end_date}T23:59:59Z',
            'per_page': 35
        }
        issues = self.get_all_pages(url, 'Fetching issues', params, 'created_at', start_date, end_date, max_workers=max_workers)
        essential_issues = []
        for issue in issues:
            if 'number' in issue and 'title' in issue and 'state' in issue and 'user' in issue and 'login' in issue['user']:
                issue_comments_url = issue['comments_url']
                initial_comment = {
                    'user': issue['user'],
                    'body': issue['body'],
                    'created_at': issue['created_at']
                }
                comments = self.get_comments_with_initial(issue_comments_url, initial_comment, issue['number'], max_workers)
                essential_issues.append({
                    'number': issue['number'],
                    'title': issue['title'],
                    'state': issue['state'],
                    'creator': issue['user']['login'],
                    'comments': comments
                })
        self.save_to_json(essential_issues, f"{repo_name.replace('/', '_')}_issues.json")
        return essential_issues

    def get_pull_requests(self, repo_name, start_date, end_date):
        max_workers = int(self.get_max_workers())
        url = f'https://api.github.com/repos/{repo_name}/pulls'
        params = {
            'state': 'all',
            'since': f'{start_date}T00:00:01Z',
            'until': f'{end_date}T23:59:59Z',
            'per_page': 35
        }
        pull_requests = self.get_all_pages(url, 'Fetching pull requests', params, 'created_at', start_date, end_date, max_workers=max_workers)
        essential_pull_requests = []
        for pr in pull_requests:
            if 'number' in pr and 'title' in pr and 'state' in pr and 'user' in pr and 'login' in pr['user']:
                pr_comments_url = pr['_links']['comments']['href']
                initial_comment = {
                    'user': pr['user'],
                    'body': pr['body'],
                    'created_at': pr['created_at']
                }
                comments = self.get_comments_with_initial(pr_comments_url, initial_comment, pr['number'], max_workers)

                commits = self.get_pull_request_commits(repo_name, pr['number'])

                labels = [label['name'] for label in pr.get('labels', [])]

                essential_pull_requests.append({
                    'number': pr['number'],
                    'title': pr['title'],
                    'state': pr['state'],
                    'creator': pr['user']['login'],
                    'comments': comments,
                    'labels': labels,
                    'commits': commits
                })
        self.save_to_json(essential_pull_requests, f"{repo_name.replace('/', '_')}_pull_requests.json")
        return essential_pull_requests

    def get_branches(self, repo_name):
        try:
            max_workers = int(self.get_max_workers())
            url = f'https://api.github.com/repos/{repo_name}/branches'
            branches = self.get_all_pages(url, 'Fetching branches', max_workers=max_workers)
            essential_branches = [{
                'name': branch['name'],
                'sha': branch['commit']['sha']
            } for branch in branches if 'name' in branch and 'commit' in branch and 'sha' in branch['commit']]
            self.save_to_json(essential_branches, f"{repo_name.replace('/', '_')}_branches.json")
            return essential_branches
        except requests.exceptions.RequestException as e:
            print(f"Erro de requisição ao GitHub: {e}")
            raise HTTPException(status_code=500, detail="Erro de comunicação com a API do GitHub.")
        except Exception as e:
            print(f"Erro inesperado: {e}")
            raise HTTPException(status_code=500, detail="Erro ao obter branches do repositório.")

class GitHubCommitViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        miner = GitHubMiner()
        commits = miner.get_commits(repo_name, start_date, end_date)

        if commits:
            return Response(commits, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Não foi possível obter os commits."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GitHubIssueViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        miner = GitHubMiner()
        issues = miner.get_issues(repo_name, start_date, end_date)

        if issues:
            return Response(issues, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Não foi possível obter as issues."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GitHubPullRequestViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        miner = GitHubMiner()
        pull_requests = miner.get_pull_requests(repo_name, start_date, end_date)

        if pull_requests:
            return Response(pull_requests, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Não foi possível obter os pull requests."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GitHubBranchViewSet(viewsets.ViewSet):
    def list(self, request):
        repo_name = request.query_params.get('repo_name')

        miner = GitHubMiner()
        branches = miner.get_branches(repo_name)

        if branches:
            return Response(branches, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Não foi possível obter as branches."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
