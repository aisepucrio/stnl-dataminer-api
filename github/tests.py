from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
import time
import requests

class GitHubAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.start_date = "2023-07-20T00:00:00Z"
        self.end_date = "2024-08-31T23:59:59Z"
        self.interval_seconds = 2  # Intervalo entre as requisições
        self.status_check_delay = 2  # Atraso entre verificações de status

        # Endpoints principais
        self.issue_pr_url = reverse('issuepullrequest-list')
        self.task_status_url = "http://localhost:8000/api/jobs/task/"

    def _add_task_id(self, response, task_list):
        """Helper para adicionar task_id se ele estiver presente na resposta"""
        data = response.json()
        task_id = data.get('task_id')
        if task_id:
            task_list.append(task_id)
            print(f"Task ID adicionado: {task_id}")
        else:
            print("task_id não encontrado na resposta:", data)

    def _mine_data_for_repo(self, repo_name, tipo):
        """Executa mineração de dados para um repositório específico e retorna lista de task_ids"""
        task_ids = []

        # Testa issues ou pull requests
        response = self.client.post(self.issue_pr_url, {
            "repo_name": repo_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "tipo": tipo
        })
        self.assertIn(response.status_code, [200, 202])
        self._add_task_id(response, task_ids)
        print(f"{tipo.capitalize()} data:", response.json())

        return task_ids

    def _check_task_statuses(self, task_ids):
        """Verifica o status de uma lista de task_ids com atraso entre verificações"""
        for task_id in task_ids:
            try:
                response = requests.get(f"{self.task_status_url}{task_id}/")
                response.raise_for_status()
                data = response.json()
                status = data.get('status')
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

            # Atraso antes de verificar o próximo status
            time.sleep(self.status_check_delay)

    def test_mine_and_check_repositories(self):
        """Recebe lista de repositórios, minera dados e verifica status das tarefas"""
        repositories = ["grafana/github-datasource", "tensortrade-org/tensortrade", "pandas-dev/pandas"]

        for repo_name in repositories:
            for tipo in ['issue', 'pull_request']:
                print(f"\nIniciando mineração para o repositório: {repo_name} como {tipo}")
                task_ids = self._mine_data_for_repo(repo_name, tipo)
                print(f"Verificando status das tasks para o repositório: {repo_name} como {tipo}")
                self._check_task_statuses(task_ids)
                # Pausa entre cada repositório
                time.sleep(self.interval_seconds)
