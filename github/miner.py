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
            metrics = APIMetrics()
            
            if response.status_code != 200:
                print(f"Erro ao verificar token: {response.status_code}", flush=True)
                return False

            # Usar a função unificada para mostrar o status
            self.check_and_log_rate_limit(response, metrics, 'core', "Verificação de Token")
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
        """Aguarda o reset do rate limit com margem de segurança"""
        try:
            response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
            metrics = APIMetrics()
            
            # Usar a função unificada para mostrar o status
            self.check_and_log_rate_limit(response, metrics, endpoint_type, "Aguardando Reset")
            
            rate_limits = response.json()['resources'][endpoint_type]
            reset_time = int(rate_limits['reset'])
            current_time = int(time.time())
            
            # Adiciona margem de segurança de 5 segundos
            wait_time = reset_time - current_time + 5
            
            if wait_time > 0:
                print(f"\n⏳ [RATE LIMIT] Aguardando {wait_time} segundos para reset (incluindo margem de segurança)...", flush=True)
                time.sleep(wait_time)
                print("✅ [RATE LIMIT] Reset concluído! Retomando operações...\n", flush=True)
                
                # Verifica novamente o rate limit após a espera
                response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
                if response.status_code == 200:
                    new_limits = response.json()['resources'][endpoint_type]
                    if int(new_limits['remaining']) > 0:
                        return True
                    else:
                        # Se ainda não resetou, aguarda mais 5 segundos
                        print("⚠️ [RATE LIMIT] Token ainda não resetou, aguardando mais 5 segundos...", flush=True)
                        time.sleep(5)
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
                return self.wait_for_rate_limit_reset('search')
            else:
                if len(self.tokens) > 1:
                    print("[RATE LIMIT] Procurando token alternativo disponível...", flush=True)
                    best_token = self.find_best_available_token()
                    
                    if best_token is not None:
                        self.current_token_index = best_token
                        self.update_auth_header()
                        print(f"[RATE LIMIT] Token alternativo encontrado! Usando token {best_token + 1}/{len(self.tokens)}", flush=True)
                        return True
                    else:
                        print("[RATE LIMIT] Nenhum token alternativo disponível. Aguardando reset...", flush=True)
                        return self.wait_for_rate_limit_reset()
                else:
                    print("[RATE LIMIT] ⚠️ ATENÇÃO: Limite atingido e não há tokens alternativos!", flush=True)
                    return self.wait_for_rate_limit_reset()
        return False

    def find_best_available_token(self):
        """
        Verifica todos os tokens e retorna o índice do melhor token disponível
        ou None se todos estiverem indisponíveis
        """
        best_token = None
        max_remaining = 0
        original_token_index = self.current_token_index
        
        for i in range(len(self.tokens)):
            # Não testar o token atual novamente
            if i == original_token_index:
                continue
            
            self.current_token_index = i
            self.update_auth_header()
            
            try:
                response = requests.get("https://api.github.com/rate_limit", headers=self.headers)
                if response.status_code == 200:
                    rate_data = response.json()['resources']
                    core_remaining = int(rate_data['core']['remaining'])
                    
                    # Se encontrar um token com mais requisições disponíveis
                    if core_remaining > max_remaining:
                        max_remaining = core_remaining
                        best_token = i
                        
                        # Se encontrar um token com requisições suficientes, usar imediatamente
                        if core_remaining > 100:
                            print(f"[TOKEN] Encontrado token {i + 1} com {core_remaining} requisições disponíveis", flush=True)
                            return i
                            
            except Exception as e:
                print(f"Erro ao verificar token {i + 1}: {str(e)}", flush=True)
        
        # Se não encontrou nenhum token com mais de 100 requisições,
        # mas encontrou algum com requisições disponíveis
        if best_token is not None and max_remaining > 0:
            print(f"[TOKEN] Usando token {best_token + 1} com {max_remaining} requisições restantes", flush=True)
            return best_token
        
        # Se não encontrou nenhum token disponível, volta para o token original
        self.current_token_index = original_token_index
        self.update_auth_header()
        return None

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

    def get_issues(self, repo_name: str, start_date: str = None, end_date: str = None, depth: str = 'basic'):
        all_issues = []
        metrics = APIMetrics()
        
        print("\n" + "="*50)
        print(f"🔍 INICIANDO EXTRAÇÃO DE ISSUES: {repo_name}")
        print(f"📅 Período: {start_date or 'início'} até {end_date or 'atual'}")
        print(f"🔎 Profundidade: {depth.upper()}")
        print("="*50 + "\n")

        try:
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print("\n" + "-"*40)
                print(f"📊 Processando período: {period_start} até {period_end}")
                print("-"*40)
                
                page = 1
                has_more_pages = True
                period_issues_count = 0

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

                    response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)
                    metrics.total_requests += 1

                    if response.status_code == 403 and 'rate limit' in response.text.lower():
                        if not self.handle_rate_limit(response, 'search'):
                            print("Falha ao recuperar após rate limit", flush=True)
                            break
                        response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)

                    data = response.json()
                    if not data.get('items'):
                        break

                    issues_in_page = len(data['items'])
                    period_issues_count += issues_in_page
                    print(f"\n📝 Página {page}: Processando {issues_in_page} issues...")

                    for issue in data['items']:
                        if 'pull_request' in issue:
                            continue

                        issue_number = issue['number']
                        
                        # Buscar timeline events
                        timeline_url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/timeline'
                        headers = {**self.headers, 'Accept': 'application/vnd.github.mockingbird-preview'}
                        timeline_response = requests.get(timeline_url, headers=headers)
                        metrics.total_requests += 1
                        
                        timeline_events = []
                        if timeline_response.status_code == 403 and 'rate limit' in timeline_response.text.lower():
                            if not self.handle_rate_limit(timeline_response, 'core'):
                                print(f"[Issues] Falha ao recuperar timeline #{issue_number} após rate limit", flush=True)
                                continue
                            timeline_response = requests.get(timeline_url, headers=headers)
                        
                        if timeline_response.status_code == 200:
                            timeline_events = [{
                                'event': event.get('event'),
                                'actor': event.get('actor', {}).get('login') if event.get('actor') else None,
                                'created_at': event.get('created_at'),
                                'assignee': event.get('assignee', {}).get('login') if event.get('assignee') else None,
                                'label': event.get('label', {}).get('name') if event.get('label') else None
                            } for event in timeline_response.json()]

                        # Buscar comentários apenas se for mineração complexa
                        comments = []
                        if depth == 'complex':
                            comments_url = issue['comments_url']
                            comments_response = requests.get(comments_url, headers=self.headers)
                            metrics.total_requests += 1
                            
                            if comments_response.status_code == 403 and 'rate limit' in comments_response.text.lower():
                                if not self.handle_rate_limit(comments_response, 'core'):
                                    print(f"[Issues] Falha ao recuperar comentários #{issue_number} após rate limit", flush=True)
                                    continue
                                comments_response = requests.get(comments_url, headers=self.headers)
                            
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

                        # Criar objeto para salvar no banco de dados
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
                            'comments_data': comments if depth == 'complex' else []
                        }

                        if depth == 'basic':
                            # Se for mineração básica, buscar Issue existente
                            existing_issue = GitHubIssue.objects.filter(issue_id=processed_issue['id']).first()
                            if existing_issue:
                                # Preservar dados complexos se existirem
                                processed_issue['comments_data'] = existing_issue.comments
                                processed_issue['timeline_events'] = existing_issue.timeline_events

                        # Atualizar ou criar Issue
                        GitHubIssue.objects.update_or_create(
                            issue_id=processed_issue['id'],
                            defaults={
                                'repository': repo_name,
                                'number': processed_issue['number'],
                                'title': processed_issue['title'],
                                'state': processed_issue['state'],
                                'creator': issue['user']['login'],
                                'assignees': processed_issue['assignees'],
                                'labels': processed_issue['labels'],
                                'milestone': processed_issue['milestone'],
                                'locked': processed_issue['locked'],
                                'created_at': processed_issue['created_at'],
                                'updated_at': processed_issue['updated_at'],
                                'closed_at': processed_issue['closed_at'],
                                'body': processed_issue['body'],
                                'comments': processed_issue.get('comments_data', existing_issue.comments if existing_issue else []),
                                'timeline_events': processed_issue.get('timeline_events', existing_issue.timeline_events if existing_issue else []),
                                'is_pull_request': False,
                                'author_association': processed_issue['author_association'],
                                'reactions': processed_issue['reactions']
                            }
                        )

                        all_issues.append(processed_issue)
                        print(f"✓ Issue #{issue_number} processada", end='\r')

                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

                print(f"\n✅ Período concluído: {period_issues_count} issues coletadas em {page} páginas")

            print("\n" + "="*50)
            print("💾 Salvando dados em JSON...")
            self.save_to_json(all_issues, f"{repo_name.replace('/', '_')}_issues.json")
            print(f"✨ Extração concluída! Total de issues coletadas: {len(all_issues)}")
            print("="*50 + "\n")
            return all_issues

        except Exception as e:
            print(f"\n❌ Erro durante a extração: {str(e)}", flush=True)
            raise RuntimeError(f"Falha na extração de issues: {str(e)}") from e
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

    def check_and_log_rate_limit(self, response, metrics, endpoint_type='core', context=""):
        """Função unificada para verificar e logar status do rate limit"""
        metrics.update_rate_limit(response.headers, endpoint_type)
        
        # Verifica se atingiu o rate limit
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            print("\n" + "="*50)
            print(f"🚫 RATE LIMIT ATINGIDO! {context}")
            print(f"Tipo de endpoint: {endpoint_type.upper()}")
            
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                wait_time = (reset_datetime - datetime.now()).total_seconds()
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
                    print("[RATE LIMIT] ⚠️ ATENÇÃO: Limite atingido e não há tokens alternativos!", flush=True)
                    self.wait_for_rate_limit_reset()
            return True
        
        # Alerta apenas quando estiver muito próximo do limite
        remaining = (metrics.search_limit_remaining if endpoint_type == 'search' 
                    else metrics.core_limit_remaining)
        if remaining and int(remaining) < 50:
            print(f"\n⚠️ ALERTA: Apenas {remaining} requisições restantes para o token atual ({endpoint_type})", flush=True)
        
        return False

    def get_pull_requests(self, repo_name: str, start_date: str = None, end_date: str = None, depth: str = 'basic'):
        all_prs = []
        metrics = APIMetrics()
        debug_buffer = []  # Buffer para acumular mensagens de debug
        
        def log_debug(pr_number, message):
            """Adiciona mensagem de debug ao buffer"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            debug_buffer.append(f"[{timestamp}][PRs][DEBUG][PR #{pr_number}] {message}")

        def log_error(pr_number, message, error=None):
            """Loga erro e imprime imediatamente"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_message = f"[{timestamp}][PRs][ERROR][PR #{pr_number}] {message}"
            if error:
                error_message += f"\nDetalhes: {str(error)}"
            print(f"\n{error_message}", flush=True)

        def flush_debug_logs():
            """Imprime e limpa o buffer de logs de debug"""
            if debug_buffer:
                print("\n=== Debug Logs ===", flush=True)
                print('\n'.join(debug_buffer), flush=True)
                print("=================\n", flush=True)
                debug_buffer.clear()

        print("\n" + "="*50)
        print(f"[PRs] 🔍 INICIANDO EXTRAÇÃO DE PULL REQUESTS: {repo_name}")
        print(f"[PRs] 📅 Período: {start_date or 'início'} até {end_date or 'atual'}")
        print(f"[PRs] 🔎 Profundidade: {depth.upper()}")
        print("="*50 + "\n")

        try:
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print("\n" + "-"*40)
                print(f"[PRs] 📊 Processando período: {period_start} até {period_end}")
                print("-"*40)
                
                base_url = "https://api.github.com/search/issues"
                page = 1
                has_more_pages = True
                period_prs_count = 0

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

                    print(f"[PRs] [Página {page}] Iniciando busca...", flush=True)
                    print(f"[PRs] Query: {query}", flush=True)

                    response = requests.get(base_url, params=params, headers=self.headers)
                    metrics.total_requests += 1
                    
                    if response.status_code == 403 and 'rate limit' in response.text.lower():
                        if not self.handle_rate_limit(response):
                            print("[PRs] Falha ao recuperar após rate limit", flush=True)
                            break
                        response = requests.get(base_url, params=params, headers=self.headers)

                    response.raise_for_status()
                    data = response.json()

                    if not data['items']:
                        print("[PRs] Nenhum PR encontrado nesta página.", flush=True)
                        break

                    print(f"[PRs] [Página {page}] Encontrados {len(data['items'])} PRs", flush=True)

                    for pr in data.get('items', []):
                        try:
                            pr_number = pr.get('number')
                            if not pr_number:
                                continue

                            log_debug(pr_number, "Iniciando processamento")
                            
                            # Buscar detalhes do PR
                            pr_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_number}'
                            pr_response = requests.get(pr_url, headers=self.headers)
                            metrics.total_requests += 1
                            
                            if pr_response.status_code == 403 and 'rate limit' in pr_response.text.lower():
                                if self.handle_rate_limit(pr_response, 'core'):
                                    # Se um novo token foi encontrado, tenta a requisição novamente
                                    pr_response = requests.get(pr_url, headers=self.headers)
                                    if pr_response.status_code != 200:
                                        print(f"[PRs] Falha ao recuperar PR #{pr_number} mesmo após troca de token", flush=True)
                                        continue
                                else:
                                    print(f"[PRs] Falha ao recuperar PR #{pr_number} após rate limit", flush=True)
                                    continue

                            pr_details = pr_response.json()
                            
                            if not pr_details:
                                log_error(pr_number, "[PRs] Detalhes do PR vazios")
                                continue
                            log_debug(pr_number, "[PRs] Detalhes obtidos com sucesso")

                            # Dados básicos que sempre serão coletados
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
                                'body': pr_details.get('body')
                            }

                            # Dados adicionais coletados apenas no modo complexo
                            if depth == 'complex':
                                # Buscar commits
                                commits_url = f'{pr_url}/commits'
                                commits_response = requests.get(commits_url, headers=self.headers)
                                metrics.total_requests += 1
                                
                                commits = []
                                if commits_response.status_code == 200:
                                    commits = commits_response.json() or []
                                    log_debug(pr_number, f"[PRs] Commits encontrados: {len(commits)}")

                                # Buscar comentários
                                comments_url = f'{pr_url}/comments'
                                comments_response = requests.get(comments_url, headers=self.headers)
                                metrics.total_requests += 1
                                
                                comments = []
                                if comments_response.status_code == 403 and 'rate limit' in comments_response.text.lower():
                                    if self.handle_rate_limit(comments_response, 'core'):
                                        comments_response = requests.get(comments_url, headers=self.headers)
                                    else:
                                        print(f"[PRs] Falha ao recuperar comentários #{pr_number} após rate limit", flush=True)
                                        continue
                                
                                if comments_response.status_code == 200:
                                    comments = comments_response.json() or []
                                    log_debug(pr_number, f"[PRs] Comentários encontrados: {len(comments)}")

                                processed_pr.update({
                                    'commits_data': [
                                        {
                                            'sha': c.get('sha'),
                                            'message': c.get('commit', {}).get('message')
                                        } for c in commits
                                    ],
                                    'comments_data': [
                                        {
                                            'user': c.get('user', {}).get('login'),
                                            'body': c.get('body')
                                        } for c in comments
                                    ]
                                })

                            # Dentro do método get_pull_requests
                            if depth == 'basic':
                                # Se for mineração básica, buscar PR existente
                                existing_pr = GitHubPullRequest.objects.filter(pr_id=processed_pr['id']).first()
                                if existing_pr:
                                    # Preservar dados complexos se existirem
                                    processed_pr['commits'] = existing_pr.commits
                                    processed_pr['comments'] = existing_pr.comments

                            # Atualizar ou criar PR
                            GitHubPullRequest.objects.update_or_create(
                                pr_id=processed_pr['id'],
                                defaults={
                                    'repository': repo_name,
                                    'number': processed_pr['number'],
                                    'title': processed_pr['title'],
                                    'state': processed_pr['state'],
                                    'creator': processed_pr['user'],
                                    'created_at': processed_pr['created_at'],
                                    'updated_at': processed_pr['updated_at'],
                                    'closed_at': processed_pr['closed_at'],
                                    'merged_at': processed_pr['merged_at'],
                                    'labels': processed_pr['labels'],
                                    'commits': processed_pr.get('commits_data', processed_pr.get('commits', [])),
                                    'comments': processed_pr.get('comments_data', processed_pr.get('comments', [])),
                                    'body': processed_pr.get('body')
                                }
                            )

                            all_prs.append(processed_pr)
                            log_debug(pr_number, "Processamento e salvamento concluídos com sucesso")
                            flush_debug_logs()

                        except Exception as e:
                            log_error(pr_number, f"Erro ao processar PR", error=e)
                            continue

                    print(f"[PRs] Progresso do período atual: {len(all_prs)} PRs coletados em {page} páginas", flush=True)
                    
                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

            print("\n" + "="*50)
            print("[PRs] 💾 Salvando dados em JSON...")
            self.save_to_json(all_prs, f"{repo_name.replace('/', '_')}_pull_requests.json")
            print(f"[PRs] ✨ Extração concluída! Total de PRs coletados: {len(all_prs)}")
            print("="*50 + "\n")
            return all_prs

        except Exception as e:
            print(f"[PRs] ❌ Erro durante a extração: {str(e)}", flush=True)
            raise RuntimeError(f"Falha na extração de PRs: {str(e)}") from e
        finally:
            self.verify_token()

    def get_branches(self, repo_name: str):
        url = f'https://api.github.com/repos/{repo_name}/branches'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                if not self.handle_rate_limit(response, 'core'):
                    print("[Branches] Falha ao recuperar após rate limit", flush=True)
                    return []
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