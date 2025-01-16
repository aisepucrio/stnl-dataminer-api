import os
import requests
import json
from dotenv import load_dotenv
from git import Repo, GitCommandError
from pydriller import Repository
from datetime import datetime, timedelta
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod
import time

class APIMetrics:
    def __init__(self):
        self.execution_start = time.time()
        self.total_requests = 0
        self.total_prs_collected = 0
        self.pages_processed = 0
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.rate_limit_limit = None
        self.requests_used = None
        self.average_time_per_request = 0
    
    def update_rate_limit(self, headers):
        """Updates rate limit information based on response headers"""
        self.rate_limit_remaining = headers.get('X-RateLimit-Remaining')
        self.rate_limit_reset = headers.get('X-RateLimit-Reset')
        self.rate_limit_limit = headers.get('X-RateLimit-Limit', 30)
        
        if self.rate_limit_limit and self.rate_limit_remaining:
            self.requests_used = int(self.rate_limit_limit) - int(self.rate_limit_remaining)
        
        if self.total_requests > 0:
            total_time = time.time() - self.execution_start
            self.average_time_per_request = total_time / self.total_requests

    def format_reset_time(self):
        """Converte o timestamp Unix para formato legível"""
        if self.rate_limit_reset:
            try:
                reset_time = datetime.fromtimestamp(int(self.rate_limit_reset))
                return reset_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return "Unknown"
        return "Unknown"

    def get_execution_time(self):
        """Calculate execution time metrics"""
        total_time = time.time() - self.execution_start
        return {
            "seconds": round(total_time, 2),
            "formatted": f"{int(total_time // 60)}min {int(total_time % 60)}s"
        }

class GitHubMiner:
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        self.tokens = []
        self.current_token_index = 0
        
        if not self.load_tokens():
            raise Exception("Falha ao inicializar tokens do GitHub. Verifique suas credenciais.")
        
        self.update_auth_header()

    def verify_token(self):
        """Verifica se o token atual é válido e tem permissões adequadas"""
        try:
            url = "https://api.github.com/rate_limit"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 401:
                print(f"Token inválido ou expirado: {self.tokens[self.current_token_index]}", flush=True)
                if len(self.tokens) > 1:
                    self.switch_token()
                    return self.verify_token()  # Tenta novamente com o próximo token
                return False
            
            if response.status_code == 403:
                rate_limits = response.json().get("rate", {})
                reset_time = rate_limits.get("reset")
                if reset_time:
                    reset_time = datetime.fromtimestamp(reset_time).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"Limite de requisições atingido. Reset em: {reset_time}", flush=True)
                
                if len(self.tokens) > 1:
                    self.switch_token()
                    return self.verify_token()  # Tenta novamente com o próximo token
                return False

            response.raise_for_status()
            rate_limits = response.json().get("rate", {})
            remaining = rate_limits.get("remaining", 0)
            
            if remaining < 100:  # Limite baixo de requisições
                print(f"Atenção: Apenas {remaining} requisições restantes", flush=True)
                if len(self.tokens) > 1:
                    self.switch_token()
                    return self.verify_token()
            
            return True

        except Exception as e:
            print(f"Erro ao verificar token: {e}", flush=True)
            return False

    def load_tokens(self):
        """Carrega tokens do GitHub a partir de um arquivo .env ou variável de ambiente"""
        load_dotenv()
        tokens_str = os.getenv("GITHUB_TOKENS")
        if not tokens_str:
            print("Nenhum token encontrado. Verifique se GITHUB_TOKENS está definido no .env", flush=True)
            return False
        
        self.tokens = [token.strip() for token in tokens_str.split(",") if token.strip()]
        if not self.tokens:
            print("Nenhum token válido encontrado após processamento", flush=True)
            return False
        
        print(f"Carregados {len(self.tokens)} tokens", flush=True)
        return self.verify_token()

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
            self.verify_token()  # Adicionada verificação do token após a troca
        else:
            remaining_requests = response.headers.get('X-RateLimit-Remaining', 'N/A')
            print(f"Requisições restantes para o token atual: {remaining_requests}", flush=True)

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
            print(f"\n[COMMITS] Iniciando extração de commits para {repo_name}", flush=True)
            print(f"[COMMITS] Período: {start_date or 'início'} até {end_date or 'atual'}", flush=True)

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
                print(f"[COMMITS] Clonando repositório: {repo_url}", flush=True)
                self.clone_repo(repo_url, repo_path)
            else:
                print(f"[COMMITS] Repositório já existe: {repo_path}", flush=True)
                self.update_repo(repo_path)

            print("[COMMITS] Iniciando análise dos commits...", flush=True)
            repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()
            essential_commits = []

            for commit in repo:
                print(f"[COMMITS] Processando commit: {commit.hash[:7]}", flush=True)
                # Cria ou recupera o autor e o committer
                author, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.author.name, email=commit.author.email if commit.author else None)
                committer, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.committer.name, email=commit.committer.email if commit.committer else None)

                # Cria ou atualiza o commit no banco de dados
                db_commit, created = GitHubCommit.objects.update_or_create(
                    sha=commit.hash,
                    defaults={
                        'repository': repo_name,
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

            print("\n[COMMITS] Salvando dados em JSON...", flush=True)
            self.save_to_json(essential_commits, f"{repo_name.replace('/', '_')}_commits.json")
            print("[COMMITS] Commits detalhados salvos no banco de dados e no JSON com sucesso.", flush=True)
            print(f"[COMMITS] Total de commits processados: {len(essential_commits)}", flush=True)
            return essential_commits

        except Exception as e:
            print(f"[COMMITS] Erro ao acessar o repositório: {e}", flush=True)
            return []
        finally:
            self.verify_token()

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
            
            # Busca detalhes adicionais para cada issue
            detailed_issues = []
            for issue in issues:
                issue_number = issue['number']
                
                # Busca comentários da issue
                comments_url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments'
                comments_response = requests.get(comments_url, headers=self.headers)
                if comments_response.status_code == 403:
                    self.handle_rate_limit(comments_response)
                    comments_response = requests.get(comments_url, headers=self.headers)
                comments = comments_response.json()
                
                # Adiciona os comentários à issue
                issue['comments_data'] = [{'user': c['user']['login'], 'body': c['body'], 'created_at': c['created_at']} for c in comments]
                detailed_issues.append(issue)

            self.save_to_json(detailed_issues, f"{repo_name.replace('/', '_')}_issues.json")

            for issue in detailed_issues:
                GitHubIssue.objects.update_or_create(
                    issue_id=issue['id'],
                    defaults={
                        'repository': repo_name,
                        'title': issue['title'],
                        'state': issue['state'],
                        'creator': issue['user']['login'],
                        'created_at': issue['created_at'],
                        'updated_at': issue['updated_at'],
                        'comments': issue['comments_data']
                    }
                )
            print("Issues salvas no banco de dados e no JSON com sucesso.", flush=True)

            return detailed_issues
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar issues: {e}", flush=True)
            return []
        finally:
            self.verify_token()

    def split_date_range(self, start_date, end_date, interval_days=1):
        """
        Divide o intervalo de datas em períodos menores
        
        Args:
            start_date (str): Data inicial no formato ISO8601 (YYYY-MM-DDTHH:MM:SSZ)
            end_date (str): Data final no formato ISO8601 (YYYY-MM-DDTHH:MM:SSZ)
            interval_days (int): Número de dias por intervalo
            
        Returns:
            generator: Gera tuplas de (data_inicio, data_fim) para cada intervalo
        """
        if not start_date or not end_date:
            yield (start_date, end_date)
            return

        # Remove o 'Z' do final e converte para datetime
        start = datetime.strptime(start_date.rstrip('Z'), "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end_date.rstrip('Z'), "%Y-%m-%dT%H:%M:%S")
        
        current = start
        while current < end:
            interval_end = min(current + timedelta(days=interval_days), end)
            yield (
                current.strftime("%Y-%m-%d"),
                interval_end.strftime("%Y-%m-%d")
            )
            current = interval_end + timedelta(days=1)

    def get_pull_requests(self, repo_name: str, start_date: str = None, end_date: str = None):
        all_prs = []
        
        print(f"\n[PRS] Iniciando extração de PRs para {repo_name}", flush=True)
        print(f"[PRS] Período total: {start_date or 'início'} até {end_date or 'atual'}", flush=True)

        try:
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print(f"\n[PRS] Processando período: {period_start} até {period_end}", flush=True)
                
                base_url = "https://api.github.com/search/issues"
                page = 1
                has_more_pages = True

                while has_more_pages:
                    query = f"repo:{repo_name} is:pr"
                    if period_start:
                        query += f" created:{period_start}"
                    if period_end:
                        query += f"..{period_end}"

                    params = {
                        'q': query,
                        'per_page': 100,
                        'page': page
                    }

                    print(f"\n[PRS] [Página {page}] Iniciando busca...", flush=True)
                    print(f"[PRS] Query: {query}", flush=True)

                    response = requests.get(base_url, params=params, headers=self.headers)

                    if response.status_code == 403:
                        print("[PRS] Rate limit atingido, alternando token...", flush=True)
                        self.handle_rate_limit(response)
                        response = requests.get(base_url, params=params, headers=self.headers)

                    response.raise_for_status()
                    data = response.json()

                    if not data['items']:
                        print("[PRS] Nenhum PR encontrado nesta página.", flush=True)
                        break

                    print(f"[PRS] [Página {page}] Encontrados {len(data['items'])} PRs", flush=True)

                    for pr in data['items']:
                        pr_number = pr['number']
                        print(f"\n[PRS] Processando PR #{pr_number}...", flush=True)
                        
                        print(f"[PRS] Buscando detalhes do PR #{pr_number}...", flush=True)
                        pr_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_number}'
                        pr_response = requests.get(pr_url, headers=self.headers)
                        if pr_response.status_code == 403:
                            print("[PRS] Rate limit atingido, alternando token...", flush=True)
                            self.handle_rate_limit(pr_response)
                            pr_response = requests.get(pr_url, headers=self.headers)
                        pr_details = pr_response.json()
                        
                        print(f"[PRS] Buscando commits do PR #{pr_number}...", flush=True)
                        commits_url = f'{pr_url}/commits'
                        commits_response = requests.get(commits_url, headers=self.headers)
                        if commits_response.status_code == 403:
                            print("[PRS] Rate limit atingido, alternando token...", flush=True)
                            self.handle_rate_limit(commits_response)
                            commits_response = requests.get(commits_url, headers=self.headers)
                        commits = commits_response.json()
                        
                        print(f"[PRS] Buscando comentários do PR #{pr_number}...", flush=True)
                        comments_url = f'{pr_url}/comments'
                        comments_response = requests.get(comments_url, headers=self.headers)
                        if comments_response.status_code == 403:
                            print("[PRS] Rate limit atingido, alternando token...", flush=True)
                            self.handle_rate_limit(comments_response)
                            comments_response = requests.get(comments_url, headers=self.headers)
                        comments = comments_response.json()

                        # Estrutura os dados do PR
                        processed_pr = {
                            'id': pr_details['id'],
                            'number': pr_details['number'],
                            'title': pr_details['title'],
                            'state': pr_details['state'],
                            'created_at': pr_details['created_at'],
                            'updated_at': pr_details['updated_at'],
                            'closed_at': pr_details.get('closed_at'),
                            'merged_at': pr_details.get('merged_at'),
                            'user': pr_details['user'],
                            'labels': pr_details['labels'],
                            'commits_data': [{'sha': c['sha'], 'message': c['commit']['message']} for c in commits],
                            'comments_data': [{'user': c['user']['login'], 'body': c['body']} for c in comments]
                        }
                        all_prs.append(processed_pr)

                    print(f"\n[PRS] Progresso do período atual: {len(all_prs)} PRs coletados em {page} páginas", flush=True)
                    
                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

            print("\n[PRS] Salvando dados em JSON...", flush=True)
            self.save_to_json(all_prs, f"{repo_name.replace('/', '_')}_pull_requests.json")

            print("[PRS] Atualizando banco de dados...", flush=True)
            for pr in all_prs:
                GitHubPullRequest.objects.update_or_create(
                    pr_id=pr['id'],
                    defaults={
                        'repository': repo_name,
                        'number': pr['number'],
                        'title': pr['title'],
                        'state': pr['state'],
                        'creator': pr['user']['login'],
                        'created_at': pr['created_at'],
                        'updated_at': pr['updated_at'],
                        'closed_at': pr.get('closed_at'),
                        'merged_at': pr.get('merged_at'),
                        'labels': [label['name'] for label in pr['labels']],
                        'commits': pr['commits_data'],
                        'comments': pr['comments_data']
                    }
                )

            print(f"\n[PRS] Extração concluída!", flush=True)
            print(f"[PRS] Total de PRs coletados: {len(all_prs)}", flush=True)
            return all_prs

        except requests.exceptions.RequestException as e:
            print(f"[PRS] Erro ao acessar pull requests: {e}", flush=True)
            return []
        finally:
            self.verify_token()

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
                    defaults={
                        'repository': repo_name,
                        'sha': branch['commit']['sha']
                    }
                )
            print("Branches salvas no banco de dados e no JSON com sucesso.", flush=True)
            return branches
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar branches: {e}", flush=True)
            return []
        finally:
            self.verify_token()
