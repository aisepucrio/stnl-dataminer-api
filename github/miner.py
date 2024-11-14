import os
import requests
import json
from dotenv import load_dotenv
from git import Repo, GitCommandError
from pydriller import Repository
from datetime import datetime
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod

class GitHubMiner:
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        self.tokens = []
        self.current_token_index = 0
        self.load_tokens() 
        self.update_auth_header()  

    def load_tokens(self):
        """Carrega tokens do GitHub a partir de um arquivo .env ou variável de ambiente"""
        load_dotenv()
        tokens_str = os.getenv("GITHUB_TOKENS")
        if tokens_str:
            self.tokens = tokens_str.split(",")
            print("Tokens carregados com sucesso.", flush=True)
        else:
            print("Nenhum token encontrado. Verifique se GITHUB_TOKENS está definido no .env", flush=True)

    def update_auth_header(self):
        """Atualiza o cabeçalho Authorization com o token atual"""
        if self.tokens:
            self.headers['Authorization'] = f'token {self.tokens[self.current_token_index]}'

    def switch_token(self):
        """Alterna para o próximo token se disponível"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.update_auth_header()
        print(f"Alternando para o próximo token. Token atual: {self.current_token_index + 1}/{len(self.tokens)}", flush=True)

    def handle_rate_limit(self, response):
        """Alterna token caso o limite de requisições seja atingido e exibe requisições restantes"""
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            print("Limite de requisições atingido. Alternando token.", flush=True)
            self.switch_token()
        else:
            remaining_requests = response.headers.get('X-RateLimit-Remaining', 'N/A')
            print(f"Requisições restantes para o token atual: {remaining_requests}", flush=True)

    def print_remaining_requests(self):
        """Exibe o número de requisições restantes no token atual"""
        try:
            url = "https://api.github.com/rate_limit"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            rate_limits = response.json().get("rate", {})
            remaining_requests = rate_limits.get("remaining", "N/A")
            limit = rate_limits.get("limit", "N/A")
            reset_time = rate_limits.get("reset", None)
            
            if reset_time:
                reset_time = datetime.fromtimestamp(reset_time).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"Requisições restantes para o token atual: {remaining_requests}/{limit}, reset em {reset_time}", flush=True)
        except Exception as e:
            print(f"Erro ao obter informações de rate limit: {e}", flush=True)

    def project_root_directory(self):
        return os.getcwd()

    def user_home_directory(self):
        return os.path.expanduser("~")

    def clone_repo(self, repo_url, clone_path):
        if not os.path.exists(clone_path):
            print(f"Cloning repo: {repo_url}", flush=True)
            Repo.clone_from(repo_url, clone_path)
        else:
            print(f"Repo already exists: {clone_path}", flush=True)
            self.update_repo(clone_path)

    def update_repo(self, repo_path):
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repo updated: {repo_path}", flush=True)
        except GitCommandError as e:
            print(f"Error updating repo: {e}", flush=True)
            raise Exception(f"Error updating repo: {e}")

    def save_to_json(self, data, filename):
        output_path = os.path.join(self.project_root_directory(), filename)
        try:
            with open(output_path, 'w') as outfile:
                json.dump(data, outfile, indent=4)
            print(f"Data successfully saved to {output_path}", flush=True)
        except Exception as e:
            print(f"Failed to save data to {output_path}: {e}", flush=True)
    
    def convert_to_iso8601(self, date):
        return date.isoformat()

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
            repo_path = os.path.join(clone_path, repo_name.split('/')[1])

            if not os.path.exists(repo_path):
                repo_url = f'https://github.com/{repo_name}'
                self.clone_repo(repo_url, repo_path)

            repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()
            essential_commits = []

            for commit in repo:
                # Cria ou recupera o autor e o committer
                author, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.author.name, email=commit.author.email if commit.author else None)
                committer, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.committer.name, email=commit.committer.email if commit.committer else None)

                # Cria ou atualiza o commit no banco de dados
                db_commit, created = GitHubCommit.objects.update_or_create(
                    sha=commit.hash,
                    defaults={
                        'message': commit.msg,
                        'date': commit.author_date,
                        'author': author,
                        'committer': committer,
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files_changed': len(commit.modified_files),
                        'in_main_branch': commit.in_main_branch,
                        'merge': commit.merge,
                        'dmm_unit_size': commit.dmm_unit_size,
                        'dmm_unit_complexity': commit.dmm_unit_complexity,
                        'dmm_unit_interfacing': commit.dmm_unit_interfacing
                    }
                )

                # Prepara dados para JSON
                commit_data = {
                    'sha': commit.hash,
                    'message': commit.msg,
                    'date': self.convert_to_iso8601(commit.author_date),
                    'author': {
                        'name': author.name,
                        'email': author.email
                    },
                    'committer': {
                        'name': committer.name,
                        'email': committer.email
                    },
                    'lines': {
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files': len(commit.modified_files)
                    },
                    'in_main_branch': commit.in_main_branch,
                    'merge': commit.merge,
                    'dmm_unit_size': commit.dmm_unit_size,
                    'dmm_unit_complexity': commit.dmm_unit_complexity,
                    'dmm_unit_interfacing': commit.dmm_unit_interfacing,
                    'modified_files': []
                }

                # Processa arquivos modificados, evita duplicados
                for mod in commit.modified_files:
                    db_mod_file, _ = GitHubModifiedFile.objects.update_or_create(
                        commit=db_commit,
                        filename=mod.filename,
                        defaults={
                            'old_path': mod.old_path,
                            'new_path': mod.new_path,
                            'change_type': mod.change_type.name,
                            'diff': mod.diff,
                            'added_lines': mod.added_lines,
                            'deleted_lines': mod.deleted_lines,
                            'complexity': mod.complexity
                        }
                    )
                    
                    # Adiciona dados do arquivo modificado ao JSON
                    mod_data = {
                        'old_path': mod.old_path,
                        'new_path': mod.new_path,
                        'filename': mod.filename,
                        'change_type': mod.change_type.name,
                        'diff': mod.diff,
                        'added_lines': mod.added_lines,
                        'deleted_lines': mod.deleted_lines,
                        'complexity': mod.complexity,
                        'methods': []
                    }

                    # Processa métodos, evita duplicados
                    for method in mod.methods:
                        GitHubMethod.objects.update_or_create(
                            modified_file=db_mod_file,
                            name=method.name,
                            defaults={
                                'complexity': method.complexity,
                                'max_nesting': getattr(method, 'max_nesting', None)
                            }
                        )

                        method_data = {
                            'name': method.name,
                            'complexity': method.complexity,
                            'max_nesting': getattr(method, 'max_nesting', None)
                        }
                        mod_data['methods'].append(method_data)

                    commit_data['modified_files'].append(mod_data)

                essential_commits.append(commit_data)

            # Salva os dados JSON
            self.save_to_json(essential_commits, f"{repo_name.replace('/', '_')}_commits.json")
            print("Commits detalhados salvos no banco de dados e no JSON com sucesso.", flush=True)
            return essential_commits

        except Exception as e:
            print(f"Erro ao acessar o repositório: {e}", flush=True)
            return []
        finally:
            self.print_remaining_requests()

    def get_issues(self, repo_name: str, start_date: str = None, end_date: str = None):
        url = f'https://api.github.com/repos/{repo_name}/issues'
        params = {
            'since': start_date,
            'until': end_date
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 403:
                self.handle_rate_limit(response)
                response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            issues = response.json()
            self.save_to_json(issues, f"{repo_name.replace('/', '_')}_issues.json")

            for issue in issues:
                GitHubIssue.objects.update_or_create(
                    issue_id=issue['id'],
                    defaults={
                        'title': issue['title'],
                        'state': issue['state'],
                        'creator': issue['user']['login'],
                        'created_at': issue['created_at'],
                        'updated_at': issue['updated_at'],
                        'comments': issue['comments']
                    }
                )
            print("Issues salvas no banco de dados e no JSON com sucesso.", flush=True)

            return issues
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar issues: {e}", flush=True)
            return []
        finally:
            self.print_remaining_requests()

    def get_pull_requests(self, repo_name: str, start_date: str = None, end_date: str = None):
        url = f'https://api.github.com/repos/{repo_name}/pulls'
        params = {
            'state': 'all',
            'since': start_date,
            'until': end_date
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 403:
                self.handle_rate_limit(response)
                response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            pull_requests = response.json()
            self.save_to_json(pull_requests, f"{repo_name.replace('/', '_')}_pull_requests.json")

            for pr in pull_requests:
                GitHubPullRequest.objects.update_or_create(
                    pr_id=pr['id'],
                    defaults={
                        'title': pr['title'],
                        'state': pr['state'],
                        'creator': pr['user']['login'],
                        'created_at': pr['created_at'],
                        'updated_at': pr['updated_at'],
                        'labels': [label['name'] for label in pr['labels']],
                        'commits': [],
                        'comments': []
                    }
                )
            print("Pull requests salvas no banco de dados e no JSON com sucesso.", flush=True)

            return pull_requests
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar pull requests: {e}", flush=True)
            return []
        finally:
            self.print_remaining_requests()

    def get_branches(self, repo_name: str):
        url = f'https://api.github.com/repos/{repo_name}/branches'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 403:
                self.handle_rate_limit(response)
                response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            branches = response.json()
            self.save_to_json(branches, f"{repo_name.replace('/', '_')}_branches.json")

            for branch in branches:
                GitHubBranch.objects.update_or_create(
                    name=branch['name'],
                    defaults={'sha': branch['commit']['sha']}
                )
            print("Branches salvas no banco de dados e no JSON com sucesso.", flush=True)
            return branches
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar branches: {e}", flush=True)
            return []
        finally:
            self.print_remaining_requests()
