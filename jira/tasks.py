from celery import shared_task
from .models import JiraIssueType, JiraIssue
import requests
from requests.auth import HTTPBasicAuth
from django.utils.dateparse import parse_datetime
from urllib.parse import quote

# @shared_task
def fetch_issue_types(jira_domain, project_key, project_id, jira_email, jira_api_token):
    url = f"https://{jira_domain}/rest/api/3/issuetype/project"
    auth = HTTPBasicAuth(jira_email, jira_api_token)
    headers = {
        "Content-Type": "application/json"
    }

    query = {
        "projectId": project_id
    }
    
    response = requests.get(url, headers=headers, params=query, auth=auth)
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

#@shared_task(ignore_result=True)
def collect_jira_issues(jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    auth = HTTPBasicAuth(jira_email, jira_api_token)

    max_results = 100  # Limite máximo de resultados por requisição
    start_at = 0       # Ponto inicial para a paginação
    total_collected = 0  # Contador de issues coletadas 
    
    # Inicia a construção da consulta JQL
    jql_query = f'project="{project_key}"'
    
    # Adiciona filtro de tipos de issues, se fornecido
    if issuetypes:
        issuetypes_jql = " OR ".join([f'issuetype="{issuetype}"' for issuetype in issuetypes])
        jql_query += f' AND ({issuetypes_jql})'
    
    # Adiciona filtro de intervalo de datas, se fornecido
    if start_date and end_date:
        # Valida e formata as datas para o formato esperado pelo Jira
        try:
            start_date_parsed = parse_datetime(start_date)
            end_date_parsed = parse_datetime(end_date)
            if not start_date_parsed or not end_date_parsed:
                raise ValueError
            jql_query += f' AND created >= "{start_date}" AND created <= "{end_date}"'
        except ValueError:
            # Opcional: Trate o erro de formato de data conforme necessário
            return {"error": "Invalid date format. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)."}
    
    # Codifica a consulta JQL para ser usada na URL
    # print(jql_query)
    encoded_jql = quote(jql_query)
    
    while True:
        jira_url = f"https://{jira_domain}/rest/api/3/search?jql={encoded_jql}&startAt={start_at}&maxResults={max_results}"
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.get(jira_url, headers=headers, auth=auth)
        if response.status_code != 200:
            return {"error": f"Failed to collect issues: {response.status_code} - {response.text}"}
        
        issues = response.json().get('issues', [])
        
        # Se não houver mais issues, sair do loop
        if not issues:
            break
        
        # Salva as issues no banco de dados
        for issue_data in issues:
            JiraIssue.objects.update_or_create(
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
        
        total_collected += len(issues)
        start_at += max_results

        # Se o número de issues coletadas for menor que o limite, todas as issues foram coletadas
        if len(issues) < max_results:
            print(total_collected)
            break
    
    return {"status": f"Collected {total_collected} issues successfully.", "total_issues": total_collected}