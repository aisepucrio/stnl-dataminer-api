from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

class GitHubAPITests(APITestCase):
    def setUp(self):
        # Configurar o cliente para os testes
        self.client = APIClient()
        self.repo_name = "esp8266/Arduino"
        self.start_date = "2024-07-20T00:00:00Z"
        self.end_date = "2024-08-31T23:59:59Z"
        
        # URLs dos endpoints
        self.commits_url = reverse('commit-list')  
        self.issues_url = reverse('issue-list')    
        self.pull_requests_url = reverse('pullrequest-list')  
        self.branches_url = reverse('branch-list')  

    def test_commits(self):
        """Testa o endpoint de commits"""
        params = {
            "repo_name": self.repo_name,
            "start_date": self.start_date,
            "end_date": self.end_date
        }
        response = self.client.get(self.commits_url, params)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
        print("Commits data:", response.json())

    def test_issues(self):
        """Testa o endpoint de issues"""
        params = {
            "repo_name": self.repo_name,
            "start_date": self.start_date,
            "end_date": self.end_date
        }
        response = self.client.get(self.issues_url, params)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
        print("Issues data:", response.json())

    def test_pull_requests(self):
        """Testa o endpoint de pull requests"""
        params = {
            "repo_name": self.repo_name,
            "start_date": self.start_date,
            "end_date": self.end_date
        }
        response = self.client.get(self.pull_requests_url, params)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
        print("Pull requests data:", response.json())

    def test_branches(self):
        """Testa o endpoint de branches"""
        params = {
            "repo_name": self.repo_name
        }
        response = self.client.get(self.branches_url, params)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
        print("Branches data:", response.json())
