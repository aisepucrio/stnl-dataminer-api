from celery import shared_task
from .models import JiraIssueType, JiraIssue
import requests
from requests.auth import HTTPBasicAuth
from django.utils.dateparse import parse_datetime
from urllib.parse import quote

def collect_issue_types(jira_domain, jira_email, jira_api_token):
    url = f"https://{jira_domain}/rest/api/3/issuetype"
    auth = HTTPBasicAuth(jira_email, jira_api_token)
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, auth=auth)

        # Verifica se o status code não é 200 (sucesso)
        if response.status_code != 200:
            # Adicione mais informações sobre a resposta na mensagem de erro
            return {"error": f"Failed to fetch issue types: {response.status_code} - {response.text}"}

        issuetypes_data = response.json()

        # Filtra e remove duplicados com base no campo `untranslatedName`
        unique_issuetypes = {}
        for issuetype in issuetypes_data:
            name = issuetype.get('name')
            untranslated_name = issuetype.get('untranslatedName')

            if name and untranslated_name:
                if untranslated_name not in unique_issuetypes:
                    unique_issuetypes[untranslated_name] = {
                        "issuetype_id": issuetype.get('id'),
                        "name": issuetype.get('untranslatedName'),
                        "domain": jira_domain,
                        "description": issuetype.get('description', '')
                    }

        # Salva os tipos de issues no banco de dados
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
        # Captura erros inesperados e retorna mais informações
        return {"error": f"Unexpected error: {str(e)}"}
    
# Função auxiliar para extrair o texto da descrição de uma issue    
def extract_description_text(description):
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

# Função para mapear os campos customizados do Jira
def get_custom_fields_mapping(jira_domain, jira_email, jira_api_token):
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

# Função para substituir os campos customizados pelo nome mapeado
def replace_custom_fields_with_names(issue_json, custom_fields_mapping):
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

def collect_jira_issues(jira_domain, project_key, jira_email, jira_api_token, issuetypes, start_date=None, end_date=None):
    auth = HTTPBasicAuth(jira_email, jira_api_token)
    max_results = 100  # Limite máximo de resultados por requisição
    start_at = 0       # Ponto inicial para a paginação
    total_collected = 0  # Contador de issues coletadas 

    # Obtém o mapeamento dos campos personalizados
    custom_fields_mapping = get_custom_fields_mapping(jira_domain, jira_email, jira_api_token)
    
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
            # Extraindo o texto da descrição
            description_json = issue_data['fields'].get('description', '')
            description_text = extract_description_text(description_json)

            # Substituindo o ID dos campos customizados pelos nomes
            issue_data = replace_custom_fields_with_names(issue_data, custom_fields_mapping)

            JiraIssue.objects.update_or_create(
                issue_id=issue_data['id'],
                defaults={
                    'key': issue_data['key'],
                    'issuetype': issue_data['fields']['issuetype']['name'],
                    'summary': issue_data['fields']['summary'],
                    'description': description_text,
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