import os
import django
import time
import requests
from django.conf import settings
from celery.result import AsyncResult
from jobs.tasks import simple_task

# Inicialize o Django antes de acessar qualquer configuração
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dataminer_api.settings')
django.setup()

# Defina a URL base do servidor Django
BASE_URL = "http://127.0.0.1:8000/api/github"

# Função para verificar o status de uma tarefa
def check_task_status(task_id):
    if not settings.CELERY_RESULT_BACKEND:
        print("Celery result backend is not configured.")
        return None

    result = AsyncResult(task_id)
    print(f"Task {task_id} status: {result.status}")
    if result.ready():
        print("Result:", result.result)
        return result.result
    else:
        print("Task is still running or failed.")
        return None

# Função para testar o endpoint de commits
def test_commits(repo_name, start_date, end_date):
    url = f"{BASE_URL}/commits/"
    params = {
        "repo_name": repo_name,
        "start_date": start_date,
        "end_date": end_date
    }
    response = requests.get(url, params=params)
    print(f"Commits status code: {response.status_code}")
    if response.status_code == 200 or 202:
        print("Commits data:", response.json())
    else:
        print("Failed to retrieve commits")

# Função para testar o endpoint de issues
def test_issues(repo_name, start_date, end_date):
    url = f"{BASE_URL}/issues/"
    params = {
        "repo_name": repo_name,
        "start_date": start_date,
        "end_date": end_date
    }
    response = requests.get(url, params=params)
    print(f"Issues status code: {response.status_code}")
    if response.status_code == 200 or 202:
        print("Issues data:", response.json())
    else:
        print("Failed to retrieve issues")

# Função para testar o endpoint de pull requests
def test_pull_requests(repo_name, start_date, end_date):
    url = f"{BASE_URL}/pull-requests/"
    params = {
        "repo_name": repo_name,
        "start_date": start_date,
        "end_date": end_date
    }
    response = requests.get(url, params=params)
    print(f"Pull requests status code: {response.status_code}")
    if response.status_code == 200 or 202:
        print("Pull requests data:", response.json())
    else:
        print("Failed to retrieve pull requests")

# Função para testar o endpoint de branches
def test_branches(repo_name):
    url = f"{BASE_URL}/branches/"
    params = {
        "repo_name": repo_name
    }
    response = requests.get(url, params=params)
    print(f"Branches status code: {response.status_code}")
    if response.status_code == 200 or 202:
        print("Branches data:", response.json())
    else:
        print("Failed to retrieve branches")

# Testando os endpoints
repo_name = "esp8266/Arduino"
start_date = "2024-07-20T00:00:00Z"
end_date = "2024-08-31T23:59:59Z"

#print("Testing commits...")
#test_commits(repo_name, start_date, end_date)

#print("\nTesting issues...")
#test_issues(repo_name, start_date, end_date)

#print("\nTesting pull requests...")
#test_pull_requests(repo_name, start_date, end_date)

print("\nTesting branches...")
test_branches(repo_name)
