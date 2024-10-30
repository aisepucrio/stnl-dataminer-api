import requests

# URL base do seu servidor Django (incluindo o prefixo "api")
BASE_URL = "http://localhost:8000/api"

# Lista de IDs das tasks para verificar
task_ids = [
    "0551bdec-d1d0-4fe4-b160-7472312b137c",
    "7b5660f5-78f2-480d-8155-6f4f777de656"
]

def check_task_status(task_id):
    """Verifica o status de uma task específica e exibe se está finalizada, pendente ou com erro."""
    try:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}/status/")
        response.raise_for_status()
        data = response.json()
        
        # Simplifica a saída apenas com o ID da task e o status
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

# Verificar o status de cada task na lista
for task_id in task_ids:
    check_task_status(task_id)
