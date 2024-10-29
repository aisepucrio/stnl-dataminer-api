from django.test import LiveServerTestCase
from .models import JiraIssue, JiraIssueType
import requests

# Defina a URL base do servidor Django
BASE_URL = "http://127.0.0.1:8000/jira"

class JiraApiTests(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super(JiraApiTests, cls).setUpClass()
        # cls.jira_domain = "spark-project.atlassian.net"
        # cls.project_key = "SPARK"
        cls.jira_domain = "stone-puc.atlassian.net"
        cls.project_key = "CSTONE"
        cls.jira_email = "gabrielmmendes19@gmail.com"
        cls.jira_api_token = "ATATT3xFfGF0xJ__SquSx3bKWcZ4dqWJyOS_MUVkZYTYY7v21dbfiptBvldgNnfYV-EwEim5385HhVlffiS4BgX1NiPYE5bsM8uXYfdO4fiyYIZZhE6hWcNmE2QLJQk6AX_XkUuHW1Xj2vGc97hfSRgejv21NVczaftxtqlQ_c-qdYSCetzZN6M=A80BA930"
        cls.issuetypes = ["Sub-task", "Story", "Task"]
        cls.start_date = "2024-09-01"
        cls.end_date = "2024-09-18"
        cls.issue_id = 5000
        cls.issuetype_id = 5200

    def setUp(self):
        # Criar uma issue no banco de dados de testes
        JiraIssue.objects.create(
            issue_id=self.issue_id,
            key="CSTONE-520",
            issuetype="Task",
            summary="Fazer alterações na API a partir das observações",
            description="Descrição da tarefa",
            created="2024-01-01T00:00:00Z",
            updated="2024-01-02T00:00:00Z",
            status="Open",
            project=self.project_key,
            creator="Gabriel",
            assignee="Gabriel",
            reporter="Gabriel"
        )

        # Criar um tipo de issue no banco de dados de testes
        JiraIssueType.objects.create(
            issuetype_id=self.issuetype_id,
            name="Teste",
            domain=self.jira_domain,
            description="Descrição do tipo de issue"
        )

    def test_collect_issues(self):
        url = f"{self.live_server_url}/jira/issues/collect/"
        data = {
            "jira_domain": self.jira_domain,
            "project_key": self.project_key,
            "jira_email": self.jira_email,
            "jira_api_token": self.jira_api_token,
            "issuetypes": self.issuetypes,
            "start_date": self.start_date,
            "end_date": self.end_date
        }
        response = requests.post(url, json=data)
        print(f"Collect issues status code: {response.status_code}")
        self.assertEqual(response.status_code, 202, "Failed to start issues collection")

    def test_list_issues(self):
        url = f"{self.live_server_url}/jira/issues/"
        response = requests.get(url)
        print(f"List issues status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to list issues.")
        issues = response.json()
        self.assertTrue(len(issues) > 0, "No issues were retrieved.")

    def test_issue_detail(self):
        url = f"{self.live_server_url}/jira/issues/{self.issue_id}/"
        response = requests.get(url)
        print(f"Issue detail status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to retrieve issue detail.")
        issue = response.json()
        self.assertIn("key", issue, "Key not found in issue details.")

    def test_delete_issue(self):
        url = f"{self.live_server_url}/jira/issues/{self.issue_id}/delete/"
        response = requests.delete(url)
        print(f"Delete issue status code: {response.status_code}")
        self.assertEqual(response.status_code, 204, f"Failed to delete issue {self.issue_id}")

    def test_collect_issue_types(self):
        url = f"{self.live_server_url}/jira/issuetypes/collect/"
        data = {
            "jira_domain": self.jira_domain,
            "jira_email": self.jira_email,
            "jira_api_token": self.jira_api_token
        }
        response = requests.post(url, json=data)
        print(f"Collect issue types status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to retrieve issue types.")

    def test_list_issue_types(self):
        url = f"{self.live_server_url}/jira/issuetypes/"
        response = requests.get(url)
        print(f"Issue types list status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to list issue types.")
        issuetypes = response.json()
        self.assertTrue(len(issuetypes) > 0, "No issue types were retrieved.")

    def test_issue_type_detail(self):
        url = f"{self.live_server_url}/jira/issuetypes/{self.issuetype_id}/"
        response = requests.get(url)
        print(f"Issue type detail status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to retrieve issue type detail.")
        issuetype = response.json()
        self.assertIn("name", issuetype, "Name not found in issue type details.")

    def test_delete_issue_type(self):
        url = f"{self.live_server_url}/jira/issuetypes/{self.issuetype_id}/delete/"
        response = requests.delete(url)
        print(f"Delete issue type status code: {response.status_code}")
        self.assertEqual(response.status_code, 204, f"Failed to delete issue type {self.issuetype_id}")
