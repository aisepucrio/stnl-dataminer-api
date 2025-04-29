from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
import time
import requests

class GitHubAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.start_date = "2023-07-20T00:00:00Z"
        self.end_date = "2024-08-31T23:59:59Z"
        self.interval_seconds = 2
        self.status_check_delay = 2

        # Main endpoints
        self.issue_pr_url = reverse('issuepullrequest-list')
        self.task_status_url = "http://localhost:8000/api/jobs/task/"

    def _add_task_id(self, response, task_list):
        """Helper to add task_id if it is present in the response"""
        data = response.json()
        task_id = data.get('task_id')
        if task_id:
            task_list.append(task_id)
            print(f"Task ID added: {task_id}")
        else:
            print("task_id not found in the response:", data)

    def _mine_data_for_repo(self, repo_name, tipo):
        """Mines data for a specific repository and returns a list of task_ids"""
        task_ids = []

        # Test issues or pull requests
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
        """Checks the status of a list of task_ids with delay between checks"""
        for task_id in task_ids:
            try:
                response = requests.get(f"{self.task_status_url}{task_id}/")
                response.raise_for_status()
                data = response.json()
                status = data.get('status')
                if status == 'SUCCESS':
                    print(f"Task ID: {task_id} - Status: Completed successfully")
                elif status == 'PENDING':
                    print(f"Task ID: {task_id} - Status: Pending")
                elif status == 'FAILURE':
                    print(f"Task ID: {task_id} - Status: Failed execution")
                else:
                    print(f"Task ID: {task_id} - Status: {status}")
            except requests.exceptions.RequestException as e:
                print(f"Error checking status for task {task_id}: {e}")

            # Delay before checking the next status
            time.sleep(self.status_check_delay)

    def test_mine_and_check_repositories(self):
        """Receives a list of repositories, mines data, and checks task statuses"""
        repositories = ["grafana/github-datasource", "tensortrade-org/tensortrade", "pandas-dev/pandas"]

        for repo_name in repositories:
            for tipo in ['issue', 'pull_request']:
                print(f"\nStarting mining for repository: {repo_name} as {tipo}")
                task_ids = self._mine_data_for_repo(repo_name, tipo)
                print(f"Checking task statuses for repository: {repo_name} as {tipo}")
                self._check_task_statuses(task_ids)
                # Pause between each repository
                time.sleep(self.interval_seconds)