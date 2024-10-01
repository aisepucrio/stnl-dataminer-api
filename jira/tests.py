from django.test import TestCase
import requests

# Defina a URL base do servidor Django
BASE_URL = "http://127.0.0.1:8000/jira"

class JiraApiTests(TestCase):

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
        cls.start_date = "2004-04-01"
        cls.end_date = "2024-09-18"
        cls.issue_id = 10466
        cls.issuetype_id = 10017

    def test_collect_issues(self):
        url = f"{BASE_URL}/issues/collect/"
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
        url = f"{BASE_URL}/issues/"
        response = requests.get(url)
        print(f"List issues status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to list issues.")
        issues = response.json()
        self.assertTrue(len(issues) > 0, "No issues were retrieved.")

    def test_issue_detail(self):
        url = f"{BASE_URL}/issues/{self.issue_id}/"
        response = requests.get(url)
        print(f"Issue detail status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to retrieve issue detail.")
        issue = response.json()
        self.assertIn("key", issue, "Key not found in issue details.")

    def test_delete_issue(self):
        url = f"{BASE_URL}/issues/{self.issue_id}/delete/"
        response = requests.delete(url)
        print(f"Delete issue status code: {response.status_code}")
        self.assertEqual(response.status_code, 204, f"Failed to delete issue {self.issue_id}")

    def test_collect_issue_types(self):
        url = f"{BASE_URL}/issuetypes/collect/"
        data = {
            "jira_domain": self.jira_domain,
            "jira_email": self.jira_email,
            "jira_api_token": self.jira_api_token
        }
        response = requests.post(url, json=data)
        print(f"Collect issue types status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to retrieve issue types.")

    def test_list_issue_types(self):
        url = f"{BASE_URL}/issuetypes/"
        response = requests.get(url)
        print(f"Issue types list status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to list issue types.")
        issuetypes = response.json()
        self.assertTrue(len(issuetypes) > 0, "No issue types were retrieved.")

    def test_issue_type_detail(self):
        url = f"{BASE_URL}/issuetypes/{self.issuetype_id}/"
        response = requests.get(url)
        print(f"Issue type detail status code: {response.status_code}")
        self.assertEqual(response.status_code, 200, "Failed to retrieve issue type detail.")
        issuetype = response.json()
        self.assertIn("name", issuetype, "Name not found in issue type details.")

    def test_delete_issue_type(self):
        url = f"{BASE_URL}/issuetypes/{self.issuetype_id}/delete/"
        response = requests.delete(url)
        print(f"Delete issue type status code: {response.status_code}")
        self.assertEqual(response.status_code, 204, f"Failed to delete issue type {self.issuetype_id}")