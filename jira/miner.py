# miner.py

import requests
from requests.auth import HTTPBasicAuth
from .models import JiraIssueType, JiraIssue
from django.utils.dateparse import parse_datetime
from urllib.parse import quote

class JiraMiner:
    def __init__(self, jira_domain, jira_email, jira_api_token):
        self.jira_domain = jira_domain
        self.jira_email = jira_email
        self.jira_api_token = jira_api_token
        self.headers = {"Accept": "application/json"}

    def collect_issue_types(self):
        url = f"https://{self.jira_domain}/rest/api/3/issuetype"
        try:
            response = requests.get(url, headers=self.headers, auth=self.auth)
            if response.status_code != 200:
                return {"error": f"Failed to fetch issue types: {response.status_code} - {response.text}"}
            issuetypes_data = response.json()
            
            unique_issuetypes = {}
            for issuetype in issuetypes_data:
                name, untranslated_name = issuetype.get('name'), issuetype.get('untranslatedName')
                if name and untranslated_name and untranslated_name not in unique_issuetypes:
                    unique_issuetypes[untranslated_name] = {
                        "issuetype_id": issuetype.get('id'),
                        "name": untranslated_name,
                        "domain": self.jira_domain,
                        "description": issuetype.get('description', '')
                    }
            
            for issuetype in unique_issuetypes.values():
                JiraIssueType.objects.update_or_create(
                    issuetype_id=issuetype['issuetype_id'],
                    defaults={
                        'name': issuetype['name'],
                        'domain': issuetype['domain'],
                        'description': issuetype['description']
                    }
                )
            return {"status": "Issue types fetched and saved successfully"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def collect_jira_issues(self, project_key, issuetypes, start_date=None, end_date=None):
        max_results, start_at, total_collected = 100, 0, 0
        custom_fields_mapping = self.get_custom_fields_mapping(self.jira_domain, self.jira_email, self.jira_api_token)
        jql_query = f'project="{project_key}"'
        
        if issuetypes:
            issuetypes_jql = " OR ".join([f'issuetype="{issuetype}"' for issuetype in issuetypes])
            jql_query += f' AND ({issuetypes_jql})'
        
        if start_date and end_date:
            try:
                start_date, end_date = parse_datetime(start_date), parse_datetime(end_date)
                jql_query += f' AND created >= "{start_date}" AND created <= "{end_date}"'
            except ValueError:
                return {"error": "Invalid date format. Use ISO 8601 format."}

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
                description = self.extract_description_text(issue_data['fields'].get('description', ''))
                issue_data = self.replace_custom_fields_with_names(issue_data, custom_fields_mapping)
                JiraIssue.objects.update_or_create(
                    issue_id=issue_data['id'],
                    defaults={
                        'key': issue_data['key'],
                        'issuetype': issue_data['fields']['issuetype']['name'],
                        'summary': issue_data['fields']['summary'],
                        'description': description,
                        'created': issue_data['fields']['created'],
                        'updated': issue_data['fields']['updated'],
                        'status': issue_data['fields']['status']['name'],
                        'priority': issue_data['fields']['priority']['name'] if issue_data['fields'].get('priority') else None,
                        'project': project_key,
                        'creator': issue_data['fields']['creator']['displayName'],
                        'assignee': issue_data['fields']['assignee']['displayName'] if issue_data['fields'].get('assignee') else None,
                        'reporter': issue_data['fields']['reporter']['displayName'] if issue_data['fields'].get('reporter') else None,
                        'all_fields': issue_data['fields']
                    }
                )
            total_collected += len(issues)
            start_at += max_results
            if len(issues) < max_results:
                break
            
        return {"status": f"Collected {total_collected} issues successfully.", "total_issues": total_collected}

    def get_custom_fields_mapping(self, jira_domain, jira_email, jira_api_token):
        url = f"https://{jira_domain}/rest/api/3/field"
        auth = HTTPBasicAuth(jira_email, jira_api_token)
        
        response = requests.get(url, auth=auth)
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

    def extract_description_text(self, description):
        if 'content' not in description:
            return ""
        
        paragraphs = description['content']
        text_parts = []
        
        for paragraph in paragraphs:
            if 'content' in paragraph:
                for content in paragraph['content']:
                    if 'text' in content:
                        text_parts.append(content['text'])
        
        return "\n".join(text_parts)

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
