# miner.py

import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from .models import JiraIssue
from django.utils.dateparse import parse_datetime
from urllib.parse import quote
import time


class JiraMiner:
    def __init__(self, jira_domain, jira_email, jira_api_token):
        self.jira_domain = jira_domain
        self.jira_email = jira_email
        self.jira_api_token = jira_api_token
        self.auth = HTTPBasicAuth(self.jira_email, self.jira_api_token)
        self.headers = {"Accept": "application/json"}

    def collect_jira_issues(self, project_key, issuetypes, start_date=None, end_date=None):
        max_results, start_at, total_collected = 100, 0, 0
        custom_fields_mapping = self.get_custom_fields_mapping(self.jira_domain, self.jira_email, self.jira_api_token)
        jql_query = f'project="{project_key}"'
        
        if issuetypes:
            issuetypes_jql = " OR ".join([f'issuetype="{issuetype}"' for issuetype in issuetypes])
            jql_query += f' AND ({issuetypes_jql})'
        
        # Validação do formato das datas
        if start_date:
            try:
                start_date_parsed = self.validate_and_parse_date(start_date)
                # Usa as datas no formato "yyyy-MM-dd HH:mm"
                jql_query += f' AND created >= "{start_date_parsed.strftime("%Y-%m-%d %H:%M")}"'
            except ValueError as e:
                return {"error": str(e)}
        if end_date:
            try:
                end_date_parsed = self.validate_and_parse_date(end_date)
                # Usa as datas no formato "yyyy-MM-dd HH:mm"
                jql_query += f' AND created <= "{end_date_parsed.strftime("%Y-%m-%d %H:%M")}"'
            except ValueError as e:
                return {"error": str(e)}


        encoded_jql = quote(jql_query)
        while True:
            jira_url = f"https://{self.jira_domain}/rest/api/3/search?jql={encoded_jql}&startAt={start_at}&maxResults={max_results}"
            response = requests.get(jira_url, headers=self.headers, auth=self.auth)
            if response.status_code != 200:
                return {"error": f"Failed to collect issues: {response.status_code} - {response.text}"}

            issues = response.json().get('issues', [])
            if not issues:
                break

            for issue_data in issues:
                current_timestamp = time.time()
                description = self.extract_words_from_description(issue_data['fields'].get('description', ''))
                issue_data = self.replace_custom_fields_with_names(issue_data, custom_fields_mapping)
                commits = self.get_commits_for_issue(issue_data['key'])
                
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
                        'time_mined': current_timestamp, # precisa ser convertido de timestamp para datetime
                        'commits': commits  # Adicionando os commits
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
    
    def get_custom_fields_mapping(self, jira_domain, jira_email, jira_api_token):
        url = f"https://{jira_domain}/rest/api/3/field"
        
        response = requests.get(url, auth=self.auth)
        if response.status_code != 200:
            raise Exception(f"Failed to get custom fields: {response.status_code} - {response.text}")
        
        fields = response.json()
        custom_fields_mapping = {}

        for field in fields:
            field_id = field.get('id')  # Exemplo: customfield_12345
            field_name = field.get('name')  # Nome legível
            if field_id.startswith('customfield_'):
                custom_fields_mapping[field_id] = field_name
        
        return custom_fields_mapping
    
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
