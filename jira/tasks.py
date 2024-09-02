from celery import shared_task
from .models import JiraIssueType, JiraIssue
import requests
from requests.auth import HTTPBasicAuth

def fetch_issue_types(jira_domain, project_key, jira_email, jira_api_token):
    url = f"https://{jira_domain}/rest/api/2/project/{project_key}/issuetype"
    auth = HTTPBasicAuth(jira_email, jira_api_token)
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        return {"error": f"Failed to fetch issue types: {response.status_code}"}
    
    issue_types_data = response.json()
    
    # Salva os tipos de issues no banco de dados
    for issue_type in issue_types_data:
        JiraIssueType.objects.update_or_create(
            domain=jira_domain,
            project_key=project_key,
            issue_type_id=issue_type['id'],
            defaults={'issue_type_name': issue_type['name']}
        )

    return {"status": "Issue types fetched and saved successfully"}

@shared_task
def collect_jira_issues(jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    auth = HTTPBasicAuth(jira_email, jira_api_token)
    
    # Se issue_types não for fornecido, buscar todos os tipos de issues do projeto
    if not issue_types:
        issue_types_queryset = JiraIssueType.objects.filter(domain=jira_domain, project_key=project_key)
        issue_types = [it.issue_type_name for it in issue_types_queryset]

    # Constrói a consulta JQL para tipos de issues e datas
    issuetypes_jql = " OR ".join([f'issuetype="{issuetype}"' for issuetype in issuetypes])
    jql_query = f'project={project_key} AND ({issuetypes_jql})'

    # Adiciona o intervalo de datas, se fornecido
    if start_date and end_date:
        jql_query += f' AND created >= "{start_date}" AND created <= "{end_date}"'

    jira_url = f"https://{jira_domain}/rest/api/2/search?jql={jql_query}"

    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.get(jira_url, headers=headers, auth=auth)
    if response.status_code != 200:
        return {"error": f"Failed to collect issues: {response.status_code}"}
    
    issues = response.json().get('issues', [])
    
    for issue_data in issues:
        issue, created = JiraIssue.objects.update_or_create(
            issue_id=issue_data['id'],
            defaults={
                'key': issue_data['key'],
                'issuetype': issue_data['fields']['issuetype']['name'],
                'summary': issue_data['fields']['summary'],
                'description': issue_data['fields'].get('description', ''),
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