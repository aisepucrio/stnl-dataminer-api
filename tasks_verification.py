import requests

BASE_URL = "http://localhost:8000/api/jobs"

task_ids = [
    "7afbe8ab-bb1f-490c-8afa-6740050b9e90"
]

def check_task_status(task_id):
    try:
        response = requests.get(f"{BASE_URL}/task/{task_id}/")
        response.raise_for_status()
        data = response.json()
        
        status = data['status']
        if status == 'SUCCESS':
            print(f"Task ID: {task_id} - Status: Finalizada com sucesso")
        elif status == 'PENDING':
            print(f"Task ID: {task_id} - Status: Pendente")
        elif status == 'FAILURE':
            print(f"Task ID: {task_id} - Status: Falha ao executar")
        else:
            print(f"Task ID: {task_id} - Status: {status}")
            
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar status da task {task_id}: {e}")

for task_id in task_ids:
    check_task_status(task_id)
