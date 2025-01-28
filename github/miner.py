import os
import requests
import json
from dotenv import load_dotenv
from git import Repo, GitCommandError
from pydriller import Repository
from datetime import datetime, timezone, timedelta
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod
import time

class APIMetrics:
    def __init__(self):
        self.execution_start = time.time()
        self.total_requests = 0
        self.total_prs_collected = 0
        self.pages_processed = 0
        # Métricas para core
        self.core_limit_remaining = None
        self.core_limit_reset = None
        self.core_limit_limit = None
        # Métricas para search
        self.search_limit_remaining = None
        self.search_limit_reset = None
        self.search_limit_limit = None
        self.requests_used = None
        self.average_time_per_request = 0
    
    def update_rate_limit(self, headers, endpoint_type='core'):
        """
        Updates rate limit information based on response headers
        
        Args:
            headers: Response headers from GitHub API
            endpoint_type: Type of endpoint being accessed ('core' or 'search')
        """
        if endpoint_type == 'search':
            self.search_limit_remaining = headers.get('X-RateLimit-Remaining')
            self.search_limit_reset = headers.get('X-RateLimit-Reset')
            self.search_limit_limit = headers.get('X-RateLimit-Limit', 30)  # Search tem limite de 30/min
            
            if self.search_limit_limit and self.search_limit_remaining:
                self.requests_used = int(self.search_limit_limit) - int(self.search_limit_remaining)
        else:  # core
            self.core_limit_remaining = headers.get('X-RateLimit-Remaining')
            self.core_limit_reset = headers.get('X-RateLimit-Reset')
            self.core_limit_limit = headers.get('X-RateLimit-Limit', 5000)  # Core tem limite de 5000/hora
            
            if self.core_limit_limit and self.core_limit_remaining:
                self.requests_used = int(self.core_limit_limit) - int(self.core_limit_remaining)
        
        if self.total_requests > 0:
            total_time = time.time() - self.execution_start
            self.average_time_per_request = total_time / self.total_requests

    def format_reset_time(self, endpoint_type='core'):
        """Converte o timestamp Unix para formato legível e considera fuso horário local"""
        reset_time = self.core_limit_reset if endpoint_type == 'core' else self.search_limit_reset
        if reset_time:
            try:
                # Converte timestamp UTC para datetime local
                reset_time_utc = datetime.fromtimestamp(int(reset_time), tz=timezone.utc)
                reset_time_local = reset_time_utc.astimezone(timezone(timedelta(hours=-3)))  # Forçando timezone de Brasília
                
                time_until_reset = reset_time_local - datetime.now().astimezone(timezone(timedelta(hours=-3)))  # Mesmo timezone para comparação
                seconds_until_reset = int(time_until_reset.total_seconds())
                
                return f"{reset_time_local.strftime('%Y-%m-%d %H:%M:%S')} (em {seconds_until_reset} segundos)"
            except Exception as e:
                print(f"Erro ao formatar tempo: {e}")
                return "Unknown"
        return "Unknown"

    def get_remaining_requests(self, endpoint_type='core'):
        """Retorna o número de requisições restantes para o tipo de endpoint"""
        return (self.core_limit_remaining if endpoint_type == 'core' 
                else self.search_limit_remaining)

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
            
            if response.status_code != 200:
                print(f"Erro ao verificar token: {response.status_code}", flush=True)
                return False

            # Pegando o rate limit do 'core' ao invés do geral
            rate_limits = response.json().get("resources", {}).get("core", {})
            remaining = rate_limits.get("remaining", 0)
            limit = rate_limits.get("limit", 0)
            
            print(f"Limite total: {limit}, Requisições restantes: {remaining}", flush=True)
            
            if remaining < 100:
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

    def wait_for_rate_limit_reset(self, endpoint_type='core'):
        try:
            response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
            rate_limits = response.json()['resources'][endpoint_type]
            reset_time = int(rate_limits['reset'])
            current_time = int(time.time())
            wait_time = reset_time - current_time + 1
            
            print("\n" + "="*50)
            print(f"📊 Status atual do {endpoint_type.upper()} Rate Limit:")
            print(f"Limite total: {rate_limits['limit']}")
            print(f"Restante: {rate_limits['remaining']}")
            print(f"Reset em: {wait_time} segundos")
            print("="*50 + "\n")
            
            if wait_time > 0:
                print(f"\n⏳ [RATE LIMIT] Aguardando {wait_time} segundos para reset...", flush=True)
                time.sleep(wait_time)
                print("✅ [RATE LIMIT] Reset concluído! Retomando operações...\n", flush=True)
                return True
        except Exception as e:
            print(f"❌ [RATE LIMIT] Erro ao aguardar reset: {str(e)}", flush=True)
            raise RuntimeError(f"Falha ao aguardar reset do rate limit: {str(e)}")
        return False

    def handle_rate_limit(self, response, endpoint_type='core'):
        """Gerencia o rate limit baseado no tipo de endpoint"""
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                wait_time = (reset_datetime - datetime.now()).total_seconds()
                
                print("\n" + "="*50)
                print("🚫 RATE LIMIT ATINGIDO!")
                print(f"Tipo de endpoint: {endpoint_type.upper()}")
                print(f"Reset programado para: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Tempo de espera necessário: {int(wait_time)} segundos")
                print("="*50 + "\n")
                
            if endpoint_type == 'search':
                print("[RATE LIMIT] Limite de busca atingido. Aguardando reset...", flush=True)
                self.wait_for_rate_limit_reset('search')
            else:
                if len(self.tokens) > 1:
                    print("[RATE LIMIT] Limite core atingido. Alternando para próximo token...", flush=True)
                    self.switch_token()
                    self.verify_token()
                else:
                    print("[RATE LIMIT] ⚠️ ATENÇÃO: Limite atingido e não há tokens alternativos disponíveis!", flush=True)
        else:
            remaining_requests = response.headers.get('X-RateLimit-Remaining', 'N/A')
            if remaining_requests != 'N/A' and int(remaining_requests) < 100:
                print(f"\n⚠️ ALERTA: Apenas {remaining_requests} requisições restantes para o token atual ({endpoint_type})", flush=True)
            else:
                print(f"Requisições restantes para o token atual ({endpoint_type}): {remaining_requests}", flush=True)

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

    def sanitize_text(self, text):
        """Remove ou substitui caracteres inválidos do texto"""
        if text is None:
            return None
        # Substitui caracteres nulos por espaço
        return text.replace('\u0000', ' ')

    def get_issues(self, repo_name: str, start_date: str = None, end_date: str = None):
        all_issues = []
        metrics = APIMetrics()
        
        print(f"\n[ISSUES] Iniciando extração de issues para {repo_name}", flush=True)
        print(f"[ISSUES] Período total: {start_date or 'início'} até {end_date or 'atual'}", flush=True)

        try:
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print(f"\n[ISSUES] Processando período: {period_start} até {period_end}", flush=True)
                
                base_url = "https://api.github.com/search/issues"
                page = 1
                has_more_pages = True

                while has_more_pages:
                    query = f"repo:{repo_name} is:issue"
                    if period_start:
                        query += f" created:{period_start}"
                    if period_end:
                        query += f"..{period_end}"

                    params = {
                        'q': query,
                        'per_page': 100,
                        'page': page
                    }

                    print(f"\n[ISSUES] [Página {page}] Iniciando busca...", flush=True)
                    print(f"[ISSUES] Query: {query}", flush=True)

                    response = requests.get(base_url, params=params, headers=self.headers)
                    metrics.total_requests += 1
                    metrics.update_rate_limit(response.headers, endpoint_type='search')

                    # Log das informações de limite
                    print("\n=== Status do Rate Limit (Search API) ===")
                    print(f"Limite total: {metrics.search_limit_limit}")
                    print(f"Requisições restantes: {metrics.search_limit_remaining}")
                    print(f"Reset em: {metrics.format_reset_time('search')}")
                    print(f"Requisições utilizadas: {metrics.requests_used}")
                    print("===========================\n")

                    if response.status_code == 403:
                        print("[ISSUES] Rate limit atingido, aguardando reset...", flush=True)
                        self.wait_for_rate_limit_reset('search')
                        # Tentar novamente após esperar
                        response = requests.get(base_url, params=params, headers=self.headers)
                        if response.status_code != 200:
                            raise RuntimeError(f"Erro após aguardar reset: {response.status_code}")

                    response.raise_for_status()
                    data = response.json()

                    if not data['items']:
                        print("[ISSUES] Nenhuma issue encontrada nesta página.", flush=True)
                        break

                    print(f"[ISSUES] [Página {page}] Encontradas {len(data['items'])} issues", flush=True)

                    for issue in data['items']:
                        # Verifica se está dentro do período final
                        if end_date and issue['created_at'] > end_date:
                            continue
                            
                        # Ignora PRs, já que serão coletados separadamente
                        if 'pull_request' in issue:
                            continue

                        issue_number = issue['number']
                        print(f"\n[ISSUES] Processando issue #{issue_number}...", flush=True)

                        # Buscar timeline events
                        print(f"[ISSUES] Buscando timeline para issue #{issue_number}...", flush=True)
                        timeline_url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/timeline'
                        headers = {**self.headers, 'Accept': 'application/vnd.github.mockingbird-preview'}
                        timeline_response = requests.get(timeline_url, headers=headers)
                        timeline_events = []
                        if timeline_response.status_code == 200:
                            timeline_events = [{
                                'event': event.get('event'),
                                'actor': event.get('actor', {}).get('login') if event.get('actor') else None,
                                'created_at': event.get('created_at'),
                                'assignee': event.get('assignee', {}).get('login') if event.get('assignee') else None,
                                'label': event.get('label', {}).get('name') if event.get('label') else None
                            } for event in timeline_response.json()]

                        # Buscar comentários
                        print(f"[ISSUES] Buscando comentários para issue #{issue_number}...", flush=True)
                        comments_url = issue['comments_url']
                        comments_response = requests.get(comments_url, headers=self.headers)
                        comments = []
                        if comments_response.status_code == 200:
                            comments = [{
                                'id': c['id'],
                                'user': c['user']['login'],
                                'body': c['body'],
                                'created_at': c['created_at'],
                                'updated_at': c['updated_at'],
                                'author_association': c['author_association'],
                                'reactions': c.get('reactions', {})
                            } for c in comments_response.json()]

                        # Estrutura os dados da issue
                        processed_issue = {
                            'id': issue['id'],
                            'number': issue['number'],
                            'title': issue['title'],
                            'state': issue['state'],
                            'locked': issue['locked'],
                            'assignees': [assignee['login'] for assignee in issue['assignees']],
                            'labels': [label['name'] for label in issue['labels']],
                            'milestone': issue['milestone']['title'] if issue['milestone'] else None,
                            'created_at': issue['created_at'],
                            'updated_at': issue['updated_at'],
                            'closed_at': issue['closed_at'],
                            'author_association': issue['author_association'],
                            'body': issue['body'],
                            'reactions': issue.get('reactions', {}),
                            'is_pull_request': False,
                            'timeline_events': timeline_events,
                            'comments_data': comments
                        }
                        all_issues.append(processed_issue)

                        # Atualizar o banco de dados
                        GitHubIssue.objects.update_or_create(
                            issue_id=processed_issue['id'],
                            defaults={
                                'repository': repo_name,
                                'number': processed_issue['number'],
                                'title': self.sanitize_text(processed_issue['title']),
                                'state': processed_issue['state'],
                                'creator': issue['user']['login'],
                                'assignees': processed_issue['assignees'],
                                'labels': processed_issue['labels'],
                                'milestone': processed_issue['milestone'],
                                'locked': processed_issue['locked'],
                                'created_at': processed_issue['created_at'],
                                'updated_at': processed_issue['updated_at'],
                                'closed_at': processed_issue['closed_at'],
                                'body': self.sanitize_text(processed_issue['body']),
                                'comments': [{**c, 'body': self.sanitize_text(c['body'])} for c in processed_issue['comments_data']],
                                'timeline_events': processed_issue['timeline_events'],
                                'is_pull_request': processed_issue['is_pull_request'],
                                'author_association': processed_issue['author_association'],
                                'reactions': processed_issue['reactions']
                            }
                        )

                    print(f"\n[ISSUES] Progresso do período atual: {len(all_issues)} issues coletadas em {page} páginas", flush=True)
                    
                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

            print("\n[ISSUES] Salvando dados em JSON...", flush=True)
            self.save_to_json(all_issues, f"{repo_name.replace('/', '_')}_issues.json")
            print(f"\n[ISSUES] Extração concluída!", flush=True)
            print(f"[ISSUES] Total de issues coletadas: {len(all_issues)}", flush=True)
            return all_issues

        except Exception as e:
            print(f"[ISSUES] Erro durante a extração: {str(e)}", flush=True)
            raise  # Re-lança a exceção com o tipo correto
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
        metrics = APIMetrics()
        
        print(f"\n[PRS] Iniciando extração de PRs para {repo_name}", flush=True)
        print(f"[PRS] Período total: {start_date or 'início'} até {end_date or 'atual'}", flush=True)

        def log_debug(pr_number, messages):
            """Função auxiliar para logs de debug"""
            if not hasattr(log_debug, 'buffer'):
                log_debug.buffer = []
            log_debug.buffer.append(f"[DEBUG][PR #{pr_number}] {messages}")

        def flush_debug_logs():
            """Função para imprimir logs acumulados"""
            if hasattr(log_debug, 'buffer') and log_debug.buffer:
                print("\n=== Debug Logs ===", flush=True)
                print('\n'.join(log_debug.buffer), flush=True)
                print("=================\n", flush=True)
                log_debug.buffer = []

        def log_error(pr_number, message, error=None):
            """Função auxiliar para logs de erro"""
            print(f"\n[ERROR][PR #{pr_number}] {message}", flush=True)
            if error:
                print(f"[ERROR][PR #{pr_number}] Detalhes: {str(error)}\n", flush=True)

        def check_rate_limit_response(response, pr_number):
            """Função auxiliar para verificar rate limit na resposta"""
            if response.status_code == 403:
                if 'rate limit' in response.text.lower():
                    print("\n" + "="*50)
                    print("🚫 RATE LIMIT ATINGIDO durante processamento do PR!")
                    print(f"PR Número: #{pr_number}")
                    
                    reset_time = response.headers.get('X-RateLimit-Reset')
                    if reset_time:
                        reset_datetime = datetime.fromtimestamp(int(reset_time))
                        wait_time = (reset_datetime - datetime.now()).total_seconds()
                        print(f"Reset programado para: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"Tempo de espera necessário: {int(wait_time)} segundos")
                    print("="*50 + "\n")
                    
                    if len(self.tokens) > 1:
                        print("[RATE LIMIT] Alternando para próximo token...", flush=True)
                        self.switch_token()
                        return True
                    else:
                        print("[RATE LIMIT] ⚠️ ATENÇÃO: Limite atingido e não há tokens alternativos!", flush=True)
                        self.wait_for_rate_limit_reset()
                        return True
                else:
                    print(f"[ERROR][PR #{pr_number}] Erro 403 não relacionado ao rate limit: {response.text}", flush=True)
            return False

        try:
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print(f"\n[PRS] Processando período: {period_start} até {period_end}", flush=True)
                print(f"[PRS] Período atual representa {self.calculate_period_days(period_start, period_end)} dias", flush=True)
                
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
                    metrics.total_requests += 1
                    metrics.update_rate_limit(response.headers, endpoint_type='search')

                    # Log das informações de limite
                    print("\n=== Status do Rate Limit (Search API) ===")
                    print(f"Limite total: {metrics.search_limit_limit}")
                    print(f"Requisições restates: {metrics.search_limit_remaining}")
                    print(f"Reset em: {metrics.format_reset_time('search')}")
                    print(f"Requisições utilizadas: {metrics.requests_used}")
                    print("===========================\n")

                    if response.status_code == 403:
                        print("[PRS] Rate limit atingido, aguardando reset...", flush=True)
                        self.wait_for_rate_limit_reset('search')
            
                        response = requests.get(base_url, params=params, headers=self.headers)
                        if response.status_code != 200:
                            raise RuntimeError(f"Erro após aguardar reset: {response.status_code}")

                    response.raise_for_status()
                    data = response.json()

                    if not data['items']:
                        print("[PRS] Nenhum PR encontrado nesta página.", flush=True)
                        break

                    print(f"[PRS] [Página {page}] Encontrados {len(data['items'])} PRs", flush=True)

                    for pr in data.get('items', []):
                        try:
                            pr_number = pr.get('number')
                            if not pr_number:
                                continue

                            log_debug(pr_number, "Iniciando processamento")
                            
                            # Busca detalhes do PR
                            pr_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_number}'
                            pr_response = requests.get(pr_url, headers=self.headers)
                            
                            if pr_response.status_code != 200:
                                if check_rate_limit_response(pr_response, pr_number):
                                    # Tenta novamente após tratar o rate limit
                                    pr_response = requests.get(pr_url, headers=self.headers)
                                    if pr_response.status_code != 200:
                                        log_error(pr_number, f"Falha ao buscar detalhes mesmo após tratar rate limit. Status: {pr_response.status_code}")
                                        flush_debug_logs()
                                        continue
                                else:
                                    log_error(pr_number, f"Falha ao buscar detalhes. Status: {pr_response.status_code}")
                                    flush_debug_logs()
                                    continue

                            pr_details = pr_response.json()
                            if not pr_details:
                                log_error(pr_number, "Detalhes do PR vazios")
                                flush_debug_logs()
                                continue

                            log_debug(pr_number, "Detalhes obtidos com sucesso")

                            # Buscar commits
                            commits_url = f'{pr_url}/commits'
                            commits_response = requests.get(commits_url, headers=self.headers)
                            
                            commits = []
                            if commits_response.status_code == 200:
                                commits = commits_response.json() or []
                                log_debug(pr_number, f"Commits encontrados: {len(commits)}")

                            # Buscar comentários
                            comments_url = f'{pr_url}/comments'
                            comments_response = requests.get(comments_url, headers=self.headers)
                            
                            comments = []
                            if comments_response.status_code == 200:
                                comments = comments_response.json() or []
                                log_debug(pr_number, f"Comentários encontrados: {len(comments)}")

                            try:
                                processed_pr = {
                                    'id': pr_details.get('id'),
                                    'number': pr_details.get('number'),
                                    'title': pr_details.get('title'),
                                    'state': pr_details.get('state'),
                                    'created_at': pr_details.get('created_at'),
                                    'updated_at': pr_details.get('updated_at'),
                                    'closed_at': pr_details.get('closed_at'),
                                    'merged_at': pr_details.get('merged_at'),
                                    'user': pr_details.get('user', {}).get('login'),
                                    'labels': [label.get('name') for label in pr_details.get('labels', []) if label],
                                    'commits_data': [],
                                    'comments_data': []
                                }

                                # Processar commits
                                if commits:
                                    processed_pr['commits_data'] = [
                                        {
                                            'sha': c.get('sha'),
                                            'message': c.get('commit', {}).get('message')
                                        } for c in commits if c
                                    ]
                                    log_debug(pr_number, f"Processados {len(processed_pr['commits_data'])} commits")

                                # Processar comentários
                                if comments:
                                    processed_pr['comments_data'] = [
                                        {
                                            'user': c.get('user', {}).get('login'),
                                            'body': c.get('body')
                                        } for c in comments if c
                                    ]
                                    log_debug(pr_number, f"Processados {len(processed_pr['comments_data'])} comentários")

                                all_prs.append(processed_pr)
                                log_debug(pr_number, "Processamento concluído com sucesso")
                                flush_debug_logs()  # Imprime todos os logs acumulados para este PR

                            except Exception as e:
                                log_error(pr_number, "Erro ao processar dados", e)
                                flush_debug_logs()
                                continue

                        except Exception as e:
                            log_error(pr_number if 'pr_number' in locals() else 'Unknown', "Erro ao processar PR", e)
                            flush_debug_logs()
                            continue

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
                        'creator': pr['user'].get('login') if isinstance(pr['user'], dict) else pr['user'],
                        'created_at': pr['created_at'],
                        'updated_at': pr['updated_at'],
                        'closed_at': pr.get('closed_at'),
                        'merged_at': pr.get('merged_at'),
                        'labels': pr['labels'],
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

    def calculate_period_days(self, start_date, end_date):
        """
        Calcula o número de dias entre duas datas
        
        Args:
            start_date (str): Data inicial no formato YYYY-MM-DD
            end_date (str): Data final no formato YYYY-MM-DD
            
        Returns:
            int: Número de dias entre as datas
        """
        if not start_date or not end_date:
            return "período completo"
            
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return (end - start).days + 1  # +1 para incluir o próprio dia