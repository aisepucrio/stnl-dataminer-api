from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import uuid
from django.utils import timezone


#///////////////////////////////////////////////////////////////////////////////////////
#run tests on docker using: docker compose run --rm web python manage.py test jira -v 2
#///////////////////////////////////////////////////////////////////////////////////////

# Imports all models and the custom exception for testing
from jira.models import (
    JiraIssue, JiraProject, JiraUser, JiraComment, JiraSprint,
    JiraIssueType, JiraHistory, JiraHistoryItem, JiraCommit,
    JiraChecklist, JiraIssueLink, JiraActivityLog
)
from jira.miner import JiraMiner  # Imported to test the exception
from jobs.models import Task


class JiraAPITests(APITestCase):
    """
    Test suite covering the happy-path scenarios and general health
    of all Jira API endpoints.
    """

    def setUp(self):
        """
        Creates a rich test dataset to ensure that all list endpoints
        have content to return.
        """
        self.user = JiraUser.objects.create(
            accountId='user-123',
            displayName='Test User',
            emailAddress='test@user.com',
            active=True,
            timeZone='America/Sao_Paulo',
            accountType='atlassian'
        )
        self.project = JiraProject.objects.create(
            id='10001', key='PROJ', name='Test Project',
            simplified=False, projectTypeKey='software'
        )
        self.issue = JiraIssue.objects.create(
            issue_id='123', issue_key='PROJ-123', project=self.project,
            summary='Login screen bug', status='To Do',
            created=timezone.now(), updated=timezone.now(),
            creator=self.user, reporter=self.user
        )
        self.issue2 = JiraIssue.objects.create(
            issue_id='124', issue_key='PROJ-124', project=self.project,
            summary='Another bug', status='To Do',
            created=timezone.now(), updated=timezone.now()
        )
        self.comment = JiraComment.objects.create(
            issue=self.issue, author=self.user,
            body="Test comment.", created=timezone.now(), updated=timezone.now()
        )
        self.sprint = JiraSprint.objects.create(id=1, name='Test Sprint', state='active', boardId=1)
        self.sprint.issues.add(self.issue)
        self.issue_type = JiraIssueType.objects.create(issue=self.issue, issuetype='Bug')
        self.history = JiraHistory.objects.create(issue=self.issue, author=self.user, created=timezone.now())
        self.history_item = JiraHistoryItem.objects.create(history=self.history, field='status', toString='In Progress')
        self.commit = JiraCommit.objects.create(
            issue=self.issue, sha='a1b2c3d4e5f6', author='Committer',
            author_email='c@test.com', message='fix', timestamp=timezone.now()
        )
        self.checklist = JiraChecklist.objects.create(
            issue=self.issue, checklist={"items": []}, progress="0%", completed=False
        )
        self.issue_link = JiraIssueLink.objects.create(
            issue=self.issue, linked_issue=self.issue2,
            link_type='Blocks', link_direction='outward'
        )
        self.activity_log = JiraActivityLog.objects.create(
            issue=self.issue, author=self.user, created=timezone.now(),
            description='Status changed'
        )

    @patch('jira.views.collect.collect_jira_issues_task')
    def test_start_jira_collection_success(self, mock_task):
        """
        [Scenario]: Successful collection request.
        [What it tests]: Ensures that a valid and complete JSON payload triggers a Celery task.
        [How it tests]: Sends a POST request to 'collect-jira-issues' with a valid 'projects' structure.
        [Expected result]: The API should return 202 Accepted.
        """
        url = reverse('collect-jira-issues')
        data = {'projects': [{'jira_domain': 'test.atlassian.net', 'project_key': 'PROJ'}]}
        mock_task.delay.return_value = MagicMock(id=str(uuid.uuid4()))
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.delay.assert_called_once()

    def test_lookup_issues_list_and_content(self):
        """
        [Scenario]: Issue list lookup.
        [What it tests]: Ensures the route works and the API response structure and data match expectations.
        [How it tests]: Sends a GET request to 'issues-list' and inspects the response content.
        [Expected result]: Returns 200 OK, and issue fields match the setup data.
        """
        url = reverse('issues-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        first_issue = next(item for item in response.data['results'] if item['issue_id'] == '123')
        self.assertEqual(first_issue['summary'], 'Login screen bug')

    def test_all_list_endpoints_return_ok(self):
        """
        [Scenario]: Health check for all list routes.
        [What it tests]: Ensures that all list endpoints are active and return successful responses.
        [How it tests]: Iterates over a list of route names and performs a GET request for each.
        [Expected result]: All endpoints should return 200 OK.
        """
        list_endpoints = [
            'jira-project-list', 'jira-user-list', 'jira-sprint-list',
            'jira-comment-list', 'jira-issuetype-list', 'jira-history-list',
            'jira-historyitem-list', 'jira-commit-list', 'jira-checklist-list',
            'jira-issuelink-list', 'jira-activitylog-list'
        ]
        for endpoint in list_endpoints:
            with self.subTest(endpoint=endpoint):
                url = reverse(endpoint)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data['results']), 1)

    def test_all_dashboard_and_utility_endpoints_return_ok(self):
        """
        [Scenario]: Health check for dashboard and utility routes.
        [What it tests]: Ensures that non-standard endpoints are active and responsive.
        [How it tests]: Iterates through each route name and performs a GET request.
        [Expected result]: All endpoints should return 200 OK.
        """
        utility_endpoints = {
            'dashboard': {}, 'graph-dashboard': {},
            'jira-date-range': {'project_id': self.project.id}
        }
        for endpoint, params in utility_endpoints.items():
            with self.subTest(endpoint=endpoint):
                url = reverse(endpoint)
                response = self.client.get(url, params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)


class JiraApiValidationTests(APITestCase):
    """
    Test suite focused on API robustness, validating
    various malformed payloads to ensure the application
    handles them gracefully and returns proper error responses.
    """
    def setUp(self):
        self.url = reverse('collect-jira-issues')
        self.base_project = {'jira_domain': 'test.atlassian.net', 'project_key': 'PROJ'}

    def test_fails_with_missing_projects_key(self):
        """[Validation]: Fails if 'projects' key is missing."""
        data = {'issuetypes': ['Bug']}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_empty_projects_list(self):
        """[Validation]: Fails if 'projects' list is empty."""
        data = {'projects': []}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_invalid_projects_type(self):
        """[Validation]: Fails if 'projects' is a string instead of a list."""
        data = {'projects': "this is not a list"}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_missing_keys_in_project_object(self):
        """[Validation]: Fails if a project object does not contain 'project_key'."""
        data = {'projects': [{'jira_domain': 'test.atlassian.net'}]}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_invalid_issuetypes_type(self):
        """[Validation]: Fails if 'issuetypes' is a string instead of a list."""
        data = {'projects': [self.base_project], 'issuetypes': 'Bug'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class JiraTasksTests(APITestCase):
    @patch("jira.tasks.JiraMiner")
    @patch("jira.tasks._reuse_or_create_task", autospec=True)
    @patch("celery.app.task.Task.request")
    def test_collect_jira_issues_task_logic_success(
        self, mock_task_request, mock_reuse, mock_jira_miner_class
    ):
        """
        [Scenario]: Successful execution of the Jira issue collection task.
        [What it tests]: Validates the full internal flow of the Celery task using mocks.
        [How it tests]: Spies on update_state, simulates miner return, and validates the final state.
        [Expected result]: Task with SUCCESS status, correct state updates, and coherent result.
        """
        from jira.tasks import collect_jira_issues_task

        # Arrange
        mock_task_request.id = str(uuid.uuid4())
        task_obj = MagicMock(spec_set=[
            "status",
            "operation",
            "error",
            "error_type",
            "token_validation_error",
            "result",
            "save"
        ])
        task_obj.result = {}
        mock_reuse.return_value = (task_obj, True)

        miner = mock_jira_miner_class.return_value
        miner.collect_jira_issues.return_value = {
            "status": "Collected 5 issues successfully.",
            "total_issues": 5
        }

        # Act
        with patch.object(collect_jira_issues_task, "update_state") as spy_state:
            res = collect_jira_issues_task.run(
                "test.atlassian.net", "PROJ", ["Bug"], None, None
            )

        # Assert
        miner.collect_jira_issues.assert_called_once_with("PROJ", ["Bug"], None, None)

        states = [c.kwargs["state"] for c in spy_state.call_args_list]
        self.assertIn("STARTED", states)
        self.assertIn("SUCCESS", states)

        self.assertEqual(task_obj.status, "SUCCESS")
        self.assertIn("operation", task_obj.result)
        self.assertIn("repository", task_obj.result)
        self.assertEqual(task_obj.result["operation"], "collect_jira_issues")
        self.assertEqual(task_obj.result["repository"], "test.atlassian.net/PROJ")

        self.assertEqual(res["status"], "Collected 5 issues successfully.")
        self.assertEqual(res["total_issues"], 5)

    @patch("jira.tasks.JiraMiner")
    @patch("jira.tasks._reuse_or_create_task", autospec=True)
    def test_collect_jira_issues_task_invalid_token(self, mock_reuse, mock_jira_miner_class):
        """
        [Scenario]: Invalid Jira token handling.
        [What it tests]: Ensures that the task correctly handles invalid token exceptions.
        [Expected result]: Task is marked as FAILURE and returns an appropriate error code.
        """
        from jira.tasks import collect_jira_issues_task

        task_obj = MagicMock(spec_set=[
            "status",
            "operation",
            "error",
            "error_type",
            "result",
            "token_validation_error",
            "save"
        ])

        mock_reuse.return_value = (task_obj, True)
        miner = mock_jira_miner_class.return_value
        miner.collect_jira_issues.side_effect = JiraMiner.NoValidJiraTokenError("Invalid token")

        res = collect_jira_issues_task.run("test.atlassian.net", "PROJ", ["Bug"], None, None)

        self.assertEqual(task_obj.status, "FAILURE")
        self.assertEqual(task_obj.error_type, "NO_VALID_JIRA_TOKEN")
        self.assertIn("Invalid token", task_obj.error)
        self.assertEqual(res["code"], "NO_VALID_JIRA_TOKEN")
