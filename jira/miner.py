# miner.py

import os
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from .models import JiraIssue
from django.utils.dateparse import parse_datetime
from urllib.parse import quote
import time
import traceback
from dotenv import load_dotenv
from django.utils import timezone

class JiraMiner:
    def __init__(self, jira_domain):
        load_dotenv()
        self.jira_domain = jira_domain.strip()
        print(f"DEBUG domínio recebido no JiraMiner: '{self.jira_domain}'", flush=True)

        # Carregando tokens
        self.tokens = [token.strip() for token in os.getenv("JIRA_API_TOKEN", "").split(",") if token.strip()]
        self.jira_email = os.getenv("JIRA_EMAIL")
        self.current_token_index = 0

        if not self.tokens or not self.jira_email:
            raise Exception("JIRA_API_TOKEN e JIRA_EMAIL devem estar configurados corretamente no .env")

        self.headers = {"Accept": "application/json"}
        self.update_auth()
        self.verify_token()

        
    def update_auth(self):
        self.auth = HTTPBasicAuth(self.jira_email, self.tokens[self.current_token_index])

    def _get_auth(self):
        return HTTPBasicAuth(self.jira_email, self.tokens[self.current_token_index])

    def switch_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.update_auth()
        print(f"[JiraMiner] 🔁 Alternando para token {self.current_token_index + 1}/{len(self.tokens)}", flush=True)


    def verify_token(self):
        for _ in range(len(self.tokens)):
            try:
                url = f"https://{self.jira_domain}/rest/api/3/myself"
                response = requests.get(url, headers=self.headers, auth=self.auth)
                if response.status_code == 200:
                    print(f"[JiraMiner] ✅ Token {self.current_token_index + 1} válido", flush=True)
                    return
                else:
                    print(f"[JiraMiner] ⚠️ Token {self.current_token_index + 1} inválido: {response.status_code}", flush=True)
            except Exception as e:
                print(f"[JiraMiner] ❌ Erro ao verificar token {self.current_token_index + 1}: {e}", flush=True)

            self.switch_token()

        raise Exception("❌ Nenhum token do Jira é válido.")



    def handle_rate_limit(self, response):
        if response.status_code == 429 or "rate limit" in response.text.lower():
            print("[JiraMiner] 🚫 Limite de requisições atingido. Tentando próximo token...", flush=True)
            original_index = self.current_token_index

            for _ in range(len(self.tokens)):
                self.switch_token()
                retry = requests.get(response.request.url, headers=self.headers, auth=self.auth)
                if retry.status_code != 429:
                    print("[JiraMiner] ✅ Novo token funcionou!", flush=True)
                    return True

            # Se nenhum token funcionou, esperar 60 segundos
            print("[JiraMiner] 🕒 Todos os tokens atingiram o limite. Aguardando 60 segundos...", flush=True)
            time.sleep(60)
            return True

        return False


    def collect_jira_issues(self, project_key, issuetypes, start_date=None, end_date=None):
        max_results, start_at, total_collected = 100, 0, 0
        custom_fields_mapping = self.get_custom_fields_mapping()

        jql_query = f'project="{project_key}"'

        if issuetypes:
            issuetypes_jql = " OR ".join([f'issuetype="{issuetype}"' for issuetype in issuetypes])
            jql_query += f' AND ({issuetypes_jql})'

        if start_date:
            start_date_parsed = self.validate_and_parse_date(start_date)
            jql_query += f' AND created >= "{start_date_parsed.strftime("%Y-%m-%d %H:%M")}"'

        if end_date:
            end_date_parsed = self.validate_and_parse_date(end_date)
            jql_query += f' AND created <= "{end_date_parsed.strftime("%Y-%m-%d %H:%M")}"'

        encoded_jql = quote(jql_query)

        while True:
            jira_url = f"https://{self.jira_domain}/rest/api/3/search?jql={encoded_jql}&startAt={start_at}&maxResults={max_results}"
            response = requests.get(jira_url, headers=self.headers, auth=self.auth)

            if self.handle_rate_limit(response):
                continue

            if response.status_code != 200:
                return {"error": f"Failed to collect issues: {response.status_code} - {response.text}"}

            issues = response.json().get('issues', [])
            if not issues:
                break

            for issue_data in issues:
                current_timestamp = timezone.make_aware(datetime.fromtimestamp(time.time()))
                description = self.extract_words_from_description(issue_data['fields'].get('description', ''))
                issue_data = self.replace_custom_fields_with_names(issue_data, custom_fields_mapping)
                commits = self.get_commits_for_issue(issue_data['key'])
                comments = self.get_comments_for_issue(issue_data['key'])
                
                # Coletando os novos dados
                history = self.get_issue_history(issue_data['key'])
                activity_log = self.get_activity_log(issue_data['key'])
                checklist = self.get_checklist(issue_data['key'])

                JiraIssue.objects.update_or_create(
                    issue_id=issue_data['id'],
                    defaults={
                        'issue_key': issue_data['key'],
                        'issuetype': issue_data['fields']['issuetype']['name'],
                        'issuetype_description': issue_data['fields']['issuetype']['description'],
                        'summary': issue_data['fields']['summary'],
                        'description': description,
                        'created': issue_data['fields']['created'],
                        'updated': issue_data['fields']['updated'],
                        'status': issue_data['fields']['status']['name'],
                        'priority': issue_data['fields']['priority']['name'] if issue_data['fields'].get('priority') else None,
                        'project': project_key,
                        'creator': issue_data['fields']['creator']['displayName'],
                        'assignee': issue_data['fields']['assignee']['displayName'] if issue_data['fields'].get('assignee') else None,
                        'all_fields': issue_data['fields'],
                        'time_mined': current_timestamp,
                        'commits': commits,
                        'comments': comments,
                        'history': history,
                        'activity_log': activity_log,
                        'checklist': checklist
                    }
                )

            total_collected += len(issues)
            start_at += max_results
            if len(issues) < max_results:
                break

        return {"status": f"Collected {total_collected} issues successfully.", "total_issues": total_collected}
    
    def get_commits_for_issue(self, issue_key):
        jira_commits_url = f"https://{self.jira_domain}/rest/dev-status/1.0/issue/detail?issueId={issue_key}&applicationType=git&dataType=repository"

        response = requests.get(jira_commits_url, headers=self.headers, auth=self.auth)
        if response.status_code != 200:
            return []
        
        details = response.json().get('detail', [])
        commits = []
        
        for detail in details:
            repositories = detail.get('repositories', [])
            for repo in repositories:
                for commit in repo.get('commits', []):
                    commits.append({
                        'id': commit.get('id'),
                        'message': commit.get('message'),
                        'author': commit.get('author', {}).get('name'),
                        'url': commit.get('url')
                    })
        return commits

    def get_comments_for_issue(self, issue_key):
        """
        Coleta os comentários de uma issue do Jira.
        
        Args:
            issue_key (str): A chave da issue (ex: PROJ-123)
            
        Returns:
            list: Lista de comentários com suas informações
        """
        comments_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}/comment"
        
        response = requests.get(comments_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_comments_for_issue(issue_key)
            
        if response.status_code != 200:
            print(f"[JiraMiner] ⚠️ Erro ao coletar comentários da issue {issue_key}: {response.status_code}", flush=True)
            return []
            
        comments_data = response.json()
        comments = []
        
        for comment in comments_data.get('comments', []):
            comments.append({
                'id': comment.get('id'),
                'body': self.extract_words_from_description(comment.get('body', '')),
                'author': comment.get('author', {}).get('displayName'),
                'created': comment.get('created'),
                'updated': comment.get('updated'),
                'reactions': comment.get('reactions', {})
            })
            
        return comments
    
    def get_issue_history(self, issue_key):
        """
        Coleta o histórico de alterações de uma issue do Jira.
        
        Args:
            issue_key (str): A chave da issue (ex: PROJ-123)
            
        Returns:
            list: Lista de alterações com suas informações
        """
        history_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}?expand=changelog"
        
        response = requests.get(history_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_issue_history(issue_key)
            
        if response.status_code != 200:
            print(f"[JiraMiner] ⚠️ Erro ao coletar histórico da issue {issue_key}: {response.status_code}", flush=True)
            return []
            
        history_data = response.json()
        history = []
        
        for change in history_data.get('changelog', {}).get('histories', []):
            history.append({
                'id': change.get('id'),
                'author': change.get('author', {}).get('displayName'),
                'created': change.get('created'),
                'items': [
                    {
                        'field': item.get('field'),
                        'fieldtype': item.get('fieldtype'),
                        'from': item.get('from'),
                        'fromString': item.get('fromString'),
                        'to': item.get('to'),
                        'toString': item.get('toString')
                    } for item in change.get('items', [])
                ]
            })
            
        return history
    
    def get_activity_log(self, issue_key):
        """
        Coleta o registro de atividades de uma issue do Jira, focando em:
        - Mudanças de status
        - Atualizações de resolução
        - Atualizações de estimativa
        - Registro de tempo
        
        Args:
            issue_key (str): A chave da issue (ex: PROJ-123)
            
        Returns:
            list: Lista de atividades com suas informações
        """
        # Primeiro, vamos obter o histórico completo da issue
        history_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}?expand=changelog"
        
        response = requests.get(history_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_activity_log(issue_key)
            
        if response.status_code != 200:
            print(f"[JiraMiner] ⚠️ Erro ao coletar registro de atividades da issue {issue_key}: {response.status_code}", flush=True)
            return []
            
        history_data = response.json()
        activities = []
        
        # Processar o histórico de mudanças
        for change in history_data.get('changelog', {}).get('histories', []):
            author = change.get('author', {}).get('displayName')
            created = change.get('created')
            
            for item in change.get('items', []):
                field = item.get('field')
                from_value = item.get('fromString')
                to_value = item.get('toString')
                
                # Mudanças de status
                if field == 'status':
                    activities.append({
                        'type': 'status_change',
                        'author': author,
                        'created': created,
                        'from': from_value,
                        'to': to_value,
                        'description': f"{author} alterou o Status {from_value} → {to_value}"
                    })
                
                # Atualizações de resolução
                elif field == 'resolution':
                    from_text = from_value if from_value else "Nenhuma"
                    to_text = to_value if to_value else "Done"
                    activities.append({
                        'type': 'resolution_change',
                        'author': author,
                        'created': created,
                        'from': from_text,
                        'to': to_text,
                        'description': f"{author} atualizou a Resolução {from_text} → {to_text}"
                    })
                
                # Atualizações de estimativa
                elif field == 'timeestimate' or field == 'remainingEstimate':
                    from_hours = str(int(float(from_value or '0') / 3600)) + 'H' if from_value else '0H'
                    to_hours = str(int(float(to_value or '0') / 3600)) + 'H' if to_value else '0H'
                    activities.append({
                        'type': 'estimate_change',
                        'author': author,
                        'created': created,
                        'from': from_hours,
                        'to': to_hours,
                        'description': f"{author} atualizou a Estimativa de trabalho restante {from_hours} → {to_hours}"
                    })
                
                # Registro de tempo
                elif field == 'timespent':
                    time_spent = str(int(float(to_value or '0') / 3600)) + 'h'
                    activities.append({
                        'type': 'time_logged',
                        'author': author,
                        'created': created,
                        'time': time_spent,
                        'description': f"{author} registrou o {time_spent}"
                    })
        
        # Ordenar atividades por data de criação (mais recentes primeiro)
        activities.sort(key=lambda x: x['created'], reverse=True)
        return activities
    
    def get_checklist(self, issue_key):
        """
        Coleta o checklist de uma issue do Jira.
        
        Args:
            issue_key (str): A chave da issue (ex: PROJ-123)
            
        Returns:
            list: Lista de itens do checklist com suas informações
        """
        # Nota: A API do Jira não tem um endpoint específico para checklist
        # Vamos tentar obter isso dos campos personalizados ou da descrição
        issue_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}"
        
        response = requests.get(issue_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_checklist(issue_key)
            
        if response.status_code != 200:
            print(f"[JiraMiner] ⚠️ Erro ao coletar checklist da issue {issue_key}: {response.status_code}", flush=True)
            return []
            
        issue_data = response.json()
        checklist = []
        
        # Verificar se há um campo personalizado para checklist
        fields = issue_data.get('fields', {})
        
        # Procurar por campos que possam conter checklist
        for field_id, field_value in fields.items():
            if isinstance(field_value, dict) and field_value.get('type') == 'checklist':
                for item in field_value.get('items', []):
                    checklist.append({
                        'id': item.get('id'),
                        'text': item.get('text'),
                        'status': item.get('status'),
                        'created': item.get('created'),
                        'updated': item.get('updated'),
                        'completed': item.get('completed'),
                        'completed_by': item.get('completedBy', {}).get('displayName') if item.get('completedBy') else None
                    })
        
        # Se não encontrou um campo de checklist, tentar extrair da descrição
        if not checklist and 'description' in fields:
            description = fields.get('description', {})
            if description and 'content' in description:
                # Procurar por listas de verificação na descrição
                checklist_items = self.extract_checklist_from_description(description)
                if checklist_items:
                    checklist = checklist_items
        
        return checklist
    
    def extract_checklist_from_description(self, description):
        """
        Tenta extrair itens de checklist da descrição de uma issue.
        
        Args:
            description (dict): A descrição da issue em formato JSON
            
        Returns:
            list: Lista de itens do checklist extraídos da descrição
        """
        checklist_items = []
        
        def traverse_content(content):
            if isinstance(content, list):
                for item in content:
                    traverse_content(item)
            elif isinstance(content, dict):
                # Verificar se é um item de checklist
                if content.get('type') == 'checkbox':
                    checklist_items.append({
                        'text': content.get('text', ''),
                        'status': 'completed' if content.get('checked', False) else 'pending',
                        'created': None,  # Não temos essa informação na descrição
                        'updated': None,
                        'completed': content.get('checked', False),
                        'completed_by': None
                    })
                # Continuar a travessia em outras chaves
                if 'content' in content:
                    traverse_content(content['content'])
        
        traverse_content(description.get('content', []))
        return checklist_items
    
    def get_custom_fields_mapping(self):
        url = f"https://{self.jira_domain}/rest/api/3/field"
        response = requests.get(url, headers=self.headers, auth=self.auth)

        if self.handle_rate_limit(response):
            return self.get_custom_fields_mapping()

        if response.status_code != 200:
            raise Exception(f"Failed to get custom fields: {response.status_code} - {response.text}")

        fields = response.json()
        return {field['id']: field['name'] for field in fields if field['id'].startswith('customfield_')}
    
    def extract_words_from_description(self, description):
        """
        Extrai todas as palavras da descrição de uma issue do Jira, lidando com casos em que o campo é vazio ou inexistente.
        
        Args:
            description (dict): O JSON representando a descrição da issue.
            
        Returns:
            str: Uma string contendo todas as palavras extraídas, separadas por espaço. Retorna uma string vazia se o campo não existir ou for vazio.
        """
        if not description or "content" not in description:
            # Retorna vazio se a descrição for None, vazia ou não contiver o campo "content"
            return ""

        words = []

        def traverse_content(content):
            if isinstance(content, list):
                for item in content:
                    traverse_content(item)
            elif isinstance(content, dict):
                # Se o conteúdo for um dicionário, verificamos se ele contém a chave "text"
                if "text" in content and isinstance(content["text"], str):
                    words.append(content["text"])
                # Continuar a travessia em outras chaves
                if "content" in content:
                    traverse_content(content["content"])

        # Inicia a travessia da estrutura de "content" na descrição
        traverse_content(description.get("content", []))

        # Retorna as palavras concatenadas em uma única string
        return " ".join(words)


    def replace_custom_fields_with_names(self, issue_json, custom_fields_mapping):
        if 'fields' not in issue_json:
            return issue_json
        
        fields = issue_json['fields']
        updated_fields = {}
        
        for key, value in fields.items():
            # Se o campo for um customfield, substituímos pelo nome
            if key in custom_fields_mapping:
                new_key = custom_fields_mapping[key]
            else:
                new_key = key
            updated_fields[new_key] = value
        
        issue_json['fields'] = updated_fields
        return issue_json

    def validate_and_parse_date(self, date_string):
        formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M"]
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {date_string}. Expected formats are: 'yyyy-MM-dd' or 'yyyy-MM-dd HH:mm'.")
