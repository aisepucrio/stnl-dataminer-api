import requests

# Defina a URL base do servidor Django
BASE_URL = "http://127.0.0.1:8000/jira"

# Função para testar o endpoint de coleta de issues
def test_collect_issues(jira_domain, project_key, jira_email, jira_api_token, issuetypes=None, start_date=None, end_date=None):
    url = f"{BASE_URL}/issues/collect/"
    data = {
        "jira_domain": jira_domain,
        "project_key": project_key,
        "jira_email": jira_email,
        "jira_api_token": jira_api_token,
        "issuetypes": issuetypes,
        "start_date": start_date,
        "end_date": end_date
    }
    response = requests.post(url, json=data)
    print(f"Collect issues status code: {response.status_code}")
    if response.status_code == 202:
        result = response.json()
        print("Issues collection started successfully.")
        print(f"Total issues collected: {result.get('total_issues', 'Unknown')}")
    else:
        print("Failed to start issues collection", response.text)

def test_list_issues():
    url = f"{BASE_URL}/issues/"
    response = requests.get(url)
    print(f"List issues status code: {response.status_code}")
    if response.status_code == 200:
        # Se a requisição for bem-sucedida, exibir as issues
        issues = response.json()
        print(f"Retrieved {len(issues)} issues successfully.")
        for issue in issues:
            print(f"Issue key: {issue['key']}, Summary: {issue['summary']}")
    else:
        print(f"Failed to list issues. Response: {response.text}")

def test_issue_detail(issue_id):
    url = f"{BASE_URL}/issues/{issue_id}/"
    response = requests.get(url)
    print(f"Issue detail status code: {response.status_code}")
    if response.status_code == 200:
        issue = response.json()
        print(f"Retrieved issue details: Key - {issue['key']}, Summary - {issue['summary']}")
    else:
        print(f"Failed to retrieve issue detail. Response: {response.text}")

def test_delete_issue(issue_id):
    url = f"{BASE_URL}/issues/{issue_id}/delete/"
    response = requests.delete(url)
    print(f"Delete issue status code: {response.status_code}")
    if response.status_code == 204:
        print(f"Issue {issue_id} deleted successfully.")
    else:
        print(f"Failed to delete issue {issue_id}. Response: {response.text}")

# Função para testar o endpoint de tipos de issues
def test_collect_issue_types(jira_domain, jira_email, jira_api_token):
    url = f"{BASE_URL}/issuetypes/collect/"
    data = {
        "jira_domain": jira_domain,
        "jira_email": jira_email,
        "jira_api_token": jira_api_token
    }
    response = requests.post(url, json=data)
    print(f"Fetch issue types status code: {response.status_code}")
    if response.status_code == 200:
        print("Issuetypes data:", response.json())
    else:
        print(f"Failed to retrieve issuetypes. Status code: {response.status_code}. Response: {response.text}")

def test_list_issue_types():
    url = f"{BASE_URL}/issuetypes/"
    response = requests.get(url)
    print(f"Issue types list status code: {response.status_code}")
    if response.status_code == 200:
        issuetypes = response.json()
        print(f"Retrieved {len(issuetypes)} issue types successfully.")
        for issuetype in issuetypes:
            print(f"Issue type: {issuetype['name']}")
    else:
        print(f"Failed to list issue types. Response: {response.text}")

def test_issue_type_detail(issuetype_id):
    url = f"{BASE_URL}/issuetypes/{issuetype_id}/"
    response = requests.get(url)
    print(f"Issue type detail status code: {response.status_code}")
    if response.status_code == 200:
        issuetype = response.json()
        print(f"Retrieved issue type details: ID - {issuetype['issuetype_id']}, Name - {issuetype['name']}")
    else:
        print(f"Failed to retrieve issue type detail. Response: {response.text}")

def test_delete_issue_type(issuetype_id):
    url = f"{BASE_URL}/issuetypes/{issuetype_id}/delete/"
    response = requests.delete(url)
    print(f"Delete issue type status code: {response.status_code}")
    if response.status_code == 204:
        print(f"Issue type {issuetype_id} deleted successfully.")
    else:
        print(f"Failed to delete issue type {issuetype_id}. Response: {response.text}")

# Testando os endpoints do Jira
jira_domain = "stone-puc.atlassian.net"
project_key = "CSTONE"
jira_email = "gabrielmmendes19@gmail.com"
jira_api_token = "ATATT3xFfGF0xJ__SquSx3bKWcZ4dqWJyOS_MUVkZYTYY7v21dbfiptBvldgNnfYV-EwEim5385HhVlffiS4BgX1NiPYE5bsM8uXYfdO4fiyYIZZhE6hWcNmE2QLJQk6AX_XkUuHW1Xj2vGc97hfSRgejv21NVczaftxtqlQ_c-qdYSCetzZN6M=A80BA930"
issuetypes = ["Sub-task","Story","Task"]
start_date = "2024-04-01"
end_date = "2024-09-18"
issue_id = 10435
project_id = 3
issuetype_id = 10016


# Testando os endpoints do Jira

# Rotas das Issues
print("\nTesting collect issues...")
test_collect_issues(jira_domain, project_key, jira_email, jira_api_token, issuetypes=issuetypes, start_date=start_date, end_date=end_date)

print("\nTesting list issues...")
test_list_issues()

print(f"\nTesting issue detail for issue ID {issue_id}...")
test_issue_detail(issue_id)

print(f"\nTesting delete issue for issue ID {issue_id}...")
test_delete_issue(issue_id)

# Rotas dos Tipos de Issues
print("Testing collect issue types...")
test_collect_issue_types(jira_domain, jira_email, jira_api_token)

print("\nTesting list issue types...")
test_list_issue_types()

print(f"\nTesting issue type detail for issue type ID {issuetype_id}...")
test_issue_type_detail(issuetype_id)

print(f"\nTesting delete issue type for issue type ID {issuetype_id}...")
test_delete_issue_type(issuetype_id)