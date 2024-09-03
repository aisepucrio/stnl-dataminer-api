from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

class JiraAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.jira_domain = "stone-puc.atlassian.net/"
        self.project_key = "CSTONE"
        self.jira_email = "gabrielmmendes19@gmail.com"
        self.jira_api_token = "ATATT3xFfGF0xJ__SquSx3bKWcZ4dqWJyOS_MUVkZYTYY7v21dbfiptBvldgNnfYV-EwEim5385HhVlffiS4BgX1NiPYE5bsM8uXYfdO4fiyYIZZhE6hWcNmE2QLJQk6AX_XkUuHW1Xj2vGc97hfSRgejv21NVczaftxtqlQ_c-qdYSCetzZN6M=A80BA930"
    
    def test_fetch_issue_types(self):
        response = self.client.post(reverse('fetch-issue-types'), {
            "jira_domain": self.jira_domain,
            "project_key": self.project_key,
            "jira_email": self.jira_email,
            "jira_api_token": self.jira_api_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('issue_types', response.data)
    
    def test_collect_issues(self):
        response = self.client.post(reverse('issue-collect'), {
            "jira_domain": self.jira_domain,
            "project_key": self.project_key,
            "jira_email": self.jira_email,
            "jira_api_token": self.jira_api_token,
            "issuetypes": ["Bug", "Storie", "Sub-task"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)