from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.utils import timezone
import uuid
from datetime import datetime

from github.models import (
    GitHubMetadata, GitHubCommit, GitHubAuthor, GitHubModifiedFile, GitHubMethod,
    GitHubIssue, GitHubPullRequest, GitHubBranch
)

from github.miners.base import BaseMiner
from jobs.models import Task

class GitHubAPITests(APITestCase):

    def setUp(self):
        self.meta = GitHubMetadata.objects.create(
            repository="pandas-dev/pandas",
            owner="pandas-dev",
            organization="pandas-dev",
            stars_count=4242,
            watchers_count=4242,
            forks_count=100,
            open_issues_count=5,
            default_branch="main",
            description="Test repo",
            html_url="https://github.com/pandas-dev/pandas",
            contributors_count=3,
            topics=["ai", "nlp"],
            languages={"Python": 10000},
            readme="README",
            labels_count=10,
            github_created_at=timezone.now(),
            github_updated_at=timezone.now(),
            is_archived=False,
            is_template=False,
            used_by_count=50,
            releases_count=2,
            time_mined=timezone.now(),
        )

        self.author = GitHubAuthor.objects.create(name="Alice", email="alice@test.com")
        self.committer = GitHubAuthor.objects.create(name="Bob", email="bob@test.com")

        self.commit = GitHubCommit.objects.create(
            repository=self.meta,
            repository_name=self.meta.repository,
            sha="a1b2c3d4e5f6a7b8c9d0"[:40],
            message="Initial commit",
            date=timezone.now(),
            author=self.author,
            committer=self.committer,
            insertions=10,
            deletions=2,
            files_changed=1,
            in_main_branch=True,
            merge=False,
            dmm_unit_size=1.0,
            dmm_unit_complexity=1.0,
            dmm_unit_interfacing=1.0,
            time_mined=timezone.now(),
        )

        self.mf = GitHubModifiedFile.objects.create(
            commit=self.commit,
            old_path=None,
            new_path="src/app.py",
            filename="src/app.py",
            change_type="M",
            diff="---",
            added_lines=10,
            deleted_lines=2,
            complexity=3,
            time_mined=timezone.now(),
        )

        self.method = GitHubMethod.objects.create(
            modified_file=self.mf,
            name="def foo()",
            complexity=2,
            max_nesting=1,
            time_mined=timezone.now(),
        )

        self.issue = GitHubIssue.objects.create(
            repository=self.meta,
            repository_name=self.meta.repository,
            issue_id=1234567890,
            number=1,
            title="Bug: something fails",
            state="open",
            creator="alice",
            assignees=["bob"],
            labels=["bug"],
            milestone=None,
            locked=False,
            github_created_at=timezone.now(),
            github_updated_at=timezone.now(),
            closed_at=None,
            body="Steps to reproduce...",
            comments=[],
            timeline_events=[],
            is_pull_request=False,
            author_association="CONTRIBUTOR",
            reactions={"+1": 1},
            time_mined=timezone.now(),
        )

        self.pr = GitHubPullRequest.objects.create(
            pr_id=987654321,
            repository=self.meta,
            repository_name=self.meta.repository,
            number=2,
            title="Add feature",
            state="open",
            creator="bob",
            github_created_at=timezone.now(),
            github_updated_at=timezone.now(),
            closed_at=None,
            merged_at=None,
            labels=["enhancement"],
            commits=[self.commit.sha],
            comments=[],
            body="Implements feature X",
            time_mined=timezone.now(),
        )

        self.branch = GitHubBranch.objects.create(
            repository=self.meta,
            repository_name=self.meta.repository,
            name="feature/x",
            sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"[:40],
            time_mined=timezone.now(),
        )

    @patch('github.views.collect.fetch_commits')
    def test_fetch_commit_success(self, mock_task):
        '''
            [Scenario]: Successful commit collection request.
            [What It Tests]: Verifies that when the fetch_commit function is called,
            it successfully creates a task.
            [How It Tests]: Mocks the function itself and attempts to create the task
            within a GitHubCommitViewSet object.
            [Expected Result]: "HTTP_202_ACCEPTED"
        '''
        url = reverse('github:commit-collect-list')
        data = {'repo_name': self.meta.repository}
        mock_task.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.apply_async.assert_called_once()

    @patch('github.views.collect.fetch_commits')
    def test_collect_commits_by_sha_success(self, mock_task):
        """
        [Scenario]: Successful collection of a specific commit (by SHA).
        [What It Tests]: Ensures the task is triggered with both 'repo_name' and 'commit_sha'.
        [How It Tests]: Sends a POST request to 'github:commit-collect-by-sha-list'.
        [Expected Result]: 202/200 response and task.apply_async called once.
        """
        url = reverse('github:commit-collect-by-sha-list')
        data = {'repo_name': self.meta.repository, 'commit_sha': 'a'*40}
        mock_task.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.apply_async.assert_called_once()

    @patch('github.views.collect.fetch_issues')
    def test_collect_issues_success(self, mock_task):
        """
        [Scenario]: Successful issue collection.
        [What It Tests]: Ensures the task is triggered with 'repo_name' and optional ISO date parameters.
        [How It Tests]: Sends a POST request to 'github:issue-collect-list'.
        [Expected Result]: 202/200 response and task.apply_async called once.
        """
        url = reverse('github:issue-collect-list')
        data = {'repo_name': self.meta.repository, 'start_date': '2025-01-01T00:00:00Z', 'end_date': '2025-01-31T23:59:59Z', 'depth': 'basic'}
        mock_task.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.apply_async.assert_called_once()

    @patch('github.views.collect.fetch_pull_requests')
    def test_collect_pull_requests_success(self, mock_task):
        """
        [Scenario]: Successful pull request collection.
        [What It Tests]: Ensures the task is triggered with 'repo_name' and optional ISO date parameters.
        [How It Tests]: Sends a POST request to 'github:pullrequest-collect-list'.
        [Expected Result]: 202/200 response and task.apply_async called once.
        """
        url = reverse('github:pullrequest-collect-list')
        data = {'repo_name': self.meta.repository, 'start_date': '2025-01-01T00:00:00Z', 'end_date': '2025-01-31T23:59:59Z', 'depth': 'basic'}
        mock_task.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.apply_async.assert_called_once()

    @patch('github.views.collect.fetch_branches')
    def test_collect_branches_success(self, mock_task):
        """
        [Scenario]: Successful branch collection.
        [What It Tests]: Ensures the task is triggered with the top-level 'repo_name'.
        [How It Tests]: Sends a POST request to 'github:branch-collect-list'.
        [Expected Result]: 202/200 response and task.apply_async called once.
        """
        url = reverse('github:branch-collect-list')
        data = {'repo_name': self.meta.repository}
        mock_task.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.apply_async.assert_called_once()

    @patch('github.views.collect.fetch_metadata')
    def test_collect_metadata_success(self, mock_task):
        """
        [Scenario]: Successful repository metadata collection.
        [What It Tests]: Ensures the task is triggered with the top-level 'repo_name'.
        [How It Tests]: Sends a POST request to 'github:metadata-collect-list'.
        [Expected Result]: 202/200 response and task.apply_async called once.
        """
        url = reverse('github:metadata-collect-list')
        data = {'repo_name': self.meta.repository}
        mock_task.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.apply_async.assert_called_once()

    @patch('github.views.collect.fetch_metadata')
    @patch('github.views.collect.fetch_branches')
    @patch('github.views.collect.fetch_pull_requests')
    @patch('github.views.collect.fetch_issues')
    @patch('github.views.collect.fetch_commits')
    def test_collect_all_success(self, mock_commits, mock_issues, mock_prs, mock_branches, mock_meta):
        """
        [Scenario]: Successful combined (collect-all) collection for multiple types.
        [What It Tests]: Ensures chained triggering of tasks through internal APIClient calls.
        [How It Tests]: Sends a POST request to 'github:collect-all-list' with repositories + collect_types.
        [Expected Result]: 202 response and each task.apply_async called at least once.
        """
        for m in (mock_commits, mock_issues, mock_prs, mock_branches, mock_meta):
            m.apply_async.return_value = MagicMock(id=str(uuid.uuid4()))

        url = reverse('github:collect-all-list')
        data = {
            'repositories': [self.meta.repository],
            'collect_types': ['commits', 'issues', 'pull_requests', 'branches', 'metadata'],
            'start_date': '2025-01-01T00:00:00Z',
            'end_date':   '2025-01-31T23:59:59Z',
            'depth': 'basic'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_commits.apply_async.assert_called()
        mock_issues.apply_async.assert_called()
        mock_prs.apply_async.assert_called()
        mock_branches.apply_async.assert_called()
        mock_meta.apply_async.assert_called()

    # Negative validations: Commits
    def test_commit_collect_missing_repo_name_returns_400(self):
        """
        [Scenario]: Missing 'repo_name'.
        [What It Tests]: Validation of required field.
        [How It Tests]: Sends a POST request without 'repo_name'.
        [Expected Result]: 400 response.
        """
        url = reverse('github:commit-collect-list')
        resp = self.client.post(url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, getattr(resp,'data',resp.content))

    def test_commit_collect_invalid_date_format_returns_400(self):
        """
        [Scenario]: Invalid date format / wrong type.
        [What It Tests]: Parsing of (ISO) dates and data types.
        [How It Tests]: Sends invalid start_date/end_date values.
        [Expected Result]: 400 response.
        """
        url = reverse('github:commit-collect-list')
        bads = [
            {'repo_name': self.meta.repository, 'start_date': '31-01-2025'},
            {'repo_name': self.meta.repository, 'end_date':   'not-a-date'},
            {'repo_name': self.meta.repository, 'start_date': 1234},
        ]
        for p in bads:
            with self.subTest(p=p):
                r = self.client.post(url, p, format='json')
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    def test_commit_collect_start_after_end_returns_400(self):
        """
        [Scenario]: Reversed date range.
        [What It Tests]: Validation of range (start <= end).
        [How It Tests]: start_date > end_date.
        [Expected Result]: 400 response.
        """
        url = reverse('github:commit-collect-list')
        p = {
            'repo_name': self.meta.repository,
            'start_date': '2025-02-01T00:00:00Z',
            'end_date':   '2025-01-01T00:00:00Z',
        }
        r = self.client.post(url, p, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    # Negative validations: Issues, PRs, Branches, Metadata
    def test_issue_collect_missing_repo_name_returns_400(self):
        url = reverse('github:issue-collect-list')
        r = self.client.post(url, {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    def test_pullrequest_collect_missing_repo_name_returns_400(self):
        url = reverse('github:pullrequest-collect-list')
        r = self.client.post(url, {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    def test_branch_collect_missing_repo_name_returns_400(self):
        url = reverse('github:branch-collect-list')
        r = self.client.post(url, {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    def test_metadata_collect_missing_repo_name_returns_400(self):
        url = reverse('github:metadata-collect-list')
        r = self.client.post(url, {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    # Negative validations: Commits by sha
    def test_commit_by_sha_missing_fields_returns_400(self):
        url = reverse('github:commit-collect-by-sha-list')

        r = self.client.post(url, {'commit_sha': 'a'*40}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

        r = self.client.post(url, {'repo_name': self.meta.repository}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))


class GitHubTasksTests(APITestCase):
    """
    Testes de lógica interna das tasks Celery (sem bater em Redis/worker).
    Sem testes de token, só fluxo e persistência de Task.
    """

    def setUp(self):
        self.meta = GitHubMetadata.objects.create(
            repository="pandas-dev/pandas",
            owner="pandas-dev",
            organization="pandas-dev",
            stars_count=1, watchers_count=1, forks_count=0, open_issues_count=0,
            default_branch="main", description="repo", html_url="https://github.com/pandas-dev/pandas",
            contributors_count=1, topics=[], languages={"Python": 1}, readme="",
            labels_count=0, github_created_at=timezone.now(), github_updated_at=timezone.now(),
            is_archived=False, is_template=False, used_by_count=0, releases_count=0, time_mined=timezone.now(),
        )
    @patch("github.tasks.Task")
    def test_create_new_task_when_no_task_pk(self, mock_task):
        from github.tasks import _reuse_or_create_task

        # Arrange
        mock_self = MagicMock()
        mock_self.request.id = str(uuid.uuid4())

        defaults = {"operation": "fetch_commits", "status": "STARTED"}
        expected_task = MagicMock()
        mock_task.objects.get_or_create.return_value = (expected_task, True)

        # Act
        task_obj, created = _reuse_or_create_task(mock_self, defaults=defaults)

        # Assert
        mock_task.objects.get_or_create.assert_called_once_with(
            task_id=mock_self.request.id, defaults=defaults
        )
        self.assertEqual(task_obj, expected_task)
        self.assertTrue(created)

    @patch("github.tasks.Task")
    def test_update_existing_task_when_task_pk_provided(self, mock_task):
        from github.tasks import _reuse_or_create_task

        # Arrange
        mock_self = MagicMock()
        mock_self.request.id = str(uuid.uuid4())

        defaults = {"operation": "fetch_commits", "status": "STARTED"}
        update_data = {**defaults, "task_id": mock_self.request.id}

        mock_task.objects.filter.return_value.update.return_value = 1
        expected_task = MagicMock()
        mock_task.objects.get.return_value = expected_task

        # Act
        task_obj, created = _reuse_or_create_task(mock_self, defaults=defaults, task_pk=42)

        # Assert
        mock_task.objects.filter.assert_called_once_with(pk=42)
        mock_task.objects.filter.return_value.update.assert_called_once_with(**update_data)
        mock_task.objects.get.assert_called_once_with(pk=42)
        self.assertEqual(task_obj, expected_task)
        self.assertFalse(created)

    @patch("github.tasks.GitHubMiner", autospec=True)                
    @patch("github.tasks._reuse_or_create_task")      
    @patch("celery.app.task.Task.request")            
    def test_fetch_commit_logic(self, mock_request, mock_reuse, mock_miner_cls):
        from github.tasks import fetch_commits

        # Arrange
        mock_request.id = str(uuid.uuid4())
        task_obj = MagicMock(spec_set=['operation','status','result','error','error_type','save'])
        mock_reuse.return_value = (task_obj, True)

        miner = mock_miner_cls.return_value
        miner.get_commits.return_value = [{"sha": "abc"}, {"sha": "def"}]

        start_dt = "2024-01-01T00:00:00Z"
        end_dt   = "2024-01-02T00:00:00Z"

        # Act
        with patch.object(fetch_commits, "update_state") as mock_state:
            res = fetch_commits.run(
                "pandas-dev/pandas", start_dt, end_dt, commit_sha="xyz", task_pk=42
            )

        # Assert
        miner.get_commits.assert_called_once_with(
            "pandas-dev/pandas",
            "2024-01-01T00:00:00Z",
            "2024-01-02T00:00:00Z",
            commit_sha="xyz",
            task_obj=task_obj,
        )

        states = [c.kwargs["state"] for c in mock_state.call_args_list]
        self.assertIn("STARTED", states)
        self.assertIn("SUCCESS", states)
        self.assertEqual(task_obj.status, "SUCCESS")
        self.assertEqual(task_obj.result["operation"], "fetch_commits")
        self.assertEqual(task_obj.result["repository"], "pandas-dev/pandas")
        self.assertEqual(task_obj.result["commit_sha"], "xyz")
        self.assertListEqual(task_obj.result["data"], [{"sha": "abc"}, {"sha": "def"}])
        self.assertEqual(res["operation"], "fetch_commits")
        self.assertEqual(res["repository"], "pandas-dev/pandas")
        self.assertEqual(res["commit_sha"], "xyz")
        self.assertListEqual(res["data"], [{"sha": "abc"}, {"sha": "def"}])
    
    @patch("github.tasks.GitHubMiner", autospec=True)
    @patch("github.tasks._reuse_or_create_task")
    @patch("celery.app.task.Task.request")
    def test_fetch_issues_logic(self, mock_request, mock_reuse, mock_miner_cls):
        from github.tasks import fetch_issues

        #Arrange
        mock_request.id = str(uuid.uuid4())
        task_obj = MagicMock(spec_set=['operation','status','result','error','error_type','save'])
        mock_reuse.return_value = (task_obj, True)

        miner = mock_miner_cls.return_value
        miner.get_repository_metadata.return_value = None
        miner.get_issues.return_value = [{"n": 1}, {"n": 2}]

        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)

        # Act
        with patch.object(fetch_issues, "update_state") as mock_state:
            res = fetch_issues.run("pandas-dev/pandas", start, end, "basic", task_pk=2)

        # Assert
        mock_miner_cls.assert_called_once_with()
        miner.get_repository_metadata.assert_called_once_with("pandas-dev/pandas")
        miner.get_issues.assert_called_once_with("pandas-dev/pandas", start, end, "basic", task_obj)

        states = [c.kwargs["state"] for c in mock_state.call_args_list]
        self.assertIn("STARTED", states)
        self.assertIn("SUCCESS", states)

        self.assertEqual(task_obj.status, "SUCCESS")
        self.assertEqual(
            task_obj.result,
            {
                "count": 2,
                "repository": "pandas-dev/pandas",
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-01-31T00:00:00",
                "depth": "basic",
            },
        )
        self.assertEqual(
            res,
            {
                "status": "SUCCESS",
                "count": 2,
                "repository": "pandas-dev/pandas",
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-01-31T00:00:00",
                "depth": "basic",
            },
        )

    @patch("github.tasks.GitHubMiner", autospec=True)
    @patch("github.tasks._reuse_or_create_task")
    @patch("celery.app.task.Task.request")
    def test_fetch_pull_requests_logic(self, mock_request, mock_reuse, mock_miner_cls):
        from github.tasks import fetch_pull_requests

        # Arrange
        mock_request.id = str(uuid.uuid4())
        task_obj = MagicMock(spec_set=["operation", "status", "result", "error", "error_type", "save"])
        mock_reuse.return_value = (task_obj, True)

        miner = mock_miner_cls.return_value
        miner.get_repository_metadata.return_value = None
        miner.get_pull_requests.return_value = [{"id": 1}, {"id": 2}, {"id": 3}]

        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)

        # Act
        with patch.object(fetch_pull_requests, "update_state") as mock_state:
            res = fetch_pull_requests.run(
                "pandas-dev/pandas", start, end, "basic", task_pk=5
            )

        # Assert
        mock_miner_cls.assert_called_once_with()
        miner.get_repository_metadata.assert_called_once_with("pandas-dev/pandas")
        miner.get_pull_requests.assert_called_once_with(
            "pandas-dev/pandas", start, end, "basic", task_obj
        )


        states = [c.kwargs["state"] for c in mock_state.call_args_list]
        self.assertIn("STARTED", states)
        self.assertIn("SUCCESS", states)

        self.assertEqual(task_obj.status, "SUCCESS")
        self.assertEqual(
            task_obj.result,
            {
                "count": 3,
                "repository": "pandas-dev/pandas",
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-01-31T00:00:00",
                "depth": "basic",
            },
        )

        self.assertEqual(
            res,
            {
                "status": "SUCCESS",
                "count": 3,
                "repository": "pandas-dev/pandas",
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-01-31T00:00:00",
                "depth": "basic",
            },
        )

    @patch('github.tasks.GitHubMiner', autospec=True)
    @patch('github.tasks._reuse_or_create_task')
    @patch('github.tasks.format_date_for_json')
    def test_fetch_branches_logic(self, mock_request, mock_reuse, mock_miner_cls):
        from github.tasks import fetch_branches

        # Arrange
        mock_request.id = str(uuid.uuid4())
        task_obj = MagicMock(spec_set=['operation','status','result','error','error_type','save'])
        mock_reuse.return_value = (task_obj, True)

        mock_miner = mock_miner_cls.return_value
        mock_miner.get_branches.return_value = ['main', 'dev', 'user']

        repo_name = "pandas-dev/pandas"

        # Act
        with patch.object(fetch_branches, "update_state") as spy_state:
            res = fetch_branches.run(repo_name, task_pk=42)

        # Assert
        mock_miner_cls.assert_called_once_with()
        mock_miner.get_repository_metadata.assert_called_once_with(repo_name)
        mock_miner.get_branches.assert_called_once_with(repo_name)

        states = [c.kwargs["state"] for c in spy_state.call_args_list]
        self.assertIn("STARTED", states)
        self.assertIn("SUCCESS", states)

        self.assertEqual(task_obj.status, "SUCCESS")
        self.assertEqual(task_obj.result["repository"], repo_name)
        self.assertEqual(task_obj.result["count"], 3)

        expected = {
            "status": "SUCCESS",
            "count": 3,
            "repository": repo_name
        }
        self.assertEqual(res, expected)

    @patch("github.tasks.GitHubMiner")               
    @patch("github.tasks._reuse_or_create_task")     
    @patch("celery.app.task.Task.request")          
    def test_fetch_metadata_success_basic(self, mock_request, mock_reuse, mock_miner_cls):
        from github.tasks import fetch_metadata, format_date_for_json

        #Arrange
        mock_request.id = str(uuid.uuid4())
        task_obj = MagicMock(spec_set=[
            'operation', 'status', 'result', 'error',
            'error_type', 'save'
        ])
        mock_reuse.return_value = (task_obj, True)

        miner = mock_miner_cls.return_value
        miner.get_repository_metadata.return_value = MagicMock(
            repository="pandas-dev/pandas",
            owner="pandas-dev/pandas",
            organization="pandas-dev/pandas",
            stars_count=100,
            watchers_count=200,
            forks_count=10,
            open_issues_count=5,
            default_branch="main",
            description="A cool AI repo",
            html_url="https://github.com/pandas-dev/pandas",
            contributors_count=3,
            topics=["ai", "nlp"],
            languages={"Python": 100},
            readme="README content",
            labels_count=2,
            github_created_at=datetime(2020, 1, 1),
            github_updated_at=datetime(2025, 1, 1),
            is_archived=False,
            is_template=False,
            used_by_count=5,
            releases_count=3,
            time_mined=datetime(2025, 1, 2)
        )

        #Act
        with patch.object(fetch_metadata, "update_state") as mock_state:
            res = fetch_metadata.run("pandas-dev/pandas", task_pk=42)

        #Assert
        mock_reuse.assert_called_once()
        mock_miner_cls.assert_called_once()
        miner.get_repository_metadata.assert_called_once_with("pandas-dev/pandas", task_obj)

        states = [c.kwargs["state"] for c in mock_state.call_args_list]
        self.assertIn("STARTED", states)
        self.assertIn("SUCCESS", states)

        self.assertEqual(task_obj.status, "SUCCESS")
        self.assertTrue(task_obj.save.called)

        expected_metadata = miner.get_repository_metadata.return_value
        expected_dict = {
            'repository': expected_metadata.repository,
            'owner': expected_metadata.owner,
            'organization': expected_metadata.organization,
            'stars_count': expected_metadata.stars_count,
            'watchers_count': expected_metadata.watchers_count,
            'forks_count': expected_metadata.forks_count,
            'open_issues_count': expected_metadata.open_issues_count,
            'default_branch': expected_metadata.default_branch,
            'description': expected_metadata.description,
            'html_url': expected_metadata.html_url,
            'contributors_count': expected_metadata.contributors_count,
            'topics': expected_metadata.topics,
            'languages': expected_metadata.languages,
            'readme': expected_metadata.readme,
            'labels_count': expected_metadata.labels_count,
            'github_created_at': format_date_for_json(expected_metadata.github_created_at),
            'github_updated_at': format_date_for_json(expected_metadata.github_updated_at),
            'is_archived': expected_metadata.is_archived,
            'is_template': expected_metadata.is_template,
            'used_by_count': expected_metadata.used_by_count,
            'releases_count': expected_metadata.releases_count,
            'time_mined': format_date_for_json(expected_metadata.time_mined)
        }

        expected_response = {
            "status": "SUCCESS",
            "repository": "pandas-dev/pandas",
            "metadata": expected_dict
        }

        self.assertEqual(res, expected_response)

    @patch("github.tasks.Task")
    @patch("github.tasks.fetch_commits")
    def test_restart_collection_commits_success(self, mock_fetch_commits, mock_task):
        from github.tasks import restart_collection

        #Arrange
        mock_self = MagicMock()
        mock_self.request.id = str(uuid.uuid4())

        task_obj = MagicMock()
        task_obj.pk = 42
        task_obj.repository = "pandas-dev/pandas"
        task_obj.type = "github_commits"
        task_obj.date_end = datetime(2025, 1, 31)
        task_obj.date_last_update = datetime(2025, 1, 1)
        mock_task.objects.get.return_value = task_obj

        mock_task_id = str(uuid.uuid4())
        mock_fetch_commits.apply_async.return_value.id = mock_task_id

        #Act
        with patch.object(restart_collection, "update_state") as mock_state:
            result = restart_collection.run(task_obj.pk)

        #Assert
        mock_task.objects.get.assert_called_once_with(pk=task_obj.pk)

        mock_fetch_commits.apply_async.assert_called_once()
        args = mock_fetch_commits.apply_async.call_args.kwargs["args"]
        self.assertEqual(args[0], "pandas-dev/pandas")    
        self.assertEqual(args[-1], task_obj.pk)    
        self.assertIsInstance(args[1], datetime)   
        self.assertIsInstance(args[2], datetime)   

        states = [c.kwargs["state"] for c in mock_state.call_args_list]
        self.assertIn("SUCCESS", states)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["spawned_task_pk"], mock_task_id)
        self.assertEqual(result["type"], "github_commits")

class TestTokenRotation(APITestCase):

    def setUp(self):
        with patch.object(
            BaseMiner, "load_tokens", 
            return_value={"success": True, 
                          "tokens_loaded": 3,
                          "valid_tokens": 3, 
                          "selected_token":{"index": 0, "remaining": 0} ,
                          "error": None}
        ):
            self.miner = BaseMiner()
        self.miner.tokens=["tokenA", "tokenB", "tokenC"]
        self.miner.current_token_index = 0
        self.miner.update_auth_header = MagicMock()

    def test_switch_token_cycles_properly(self):
        self.assertEqual(self.miner.current_token_index, 0)

        self.miner.switch_token()
        self.assertEqual(self.miner.current_token_index, 1)
        self.miner.update_auth_header.assert_called_once()

        self.miner.switch_token()
        self.assertEqual(self.miner.current_token_index, 2)

        self.miner.switch_token()
        self.assertEqual(self.miner.current_token_index, 0)

    def test_handle_rate_limit_switches_to_best_token(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "API rate limit exceeded"

        self.miner.tokens = ["tok1", "tok2", "tok3"]
        self.miner.find_best_available_token = MagicMock(return_value=1)
        self.miner.update_auth_header = MagicMock()

        rotated = self.miner.handle_rate_limit(mock_response)

        self.assertTrue(rotated)
        self.miner.find_best_available_token.assert_called_once()
        self.miner.update_auth_header.assert_called_once()
        self.assertEqual(self.miner.current_token_index, 1)

    def test_handle_rate_limit_waits_if_no_tokens_available(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "rate limit exceeded"

        self.miner.find_best_available_token = MagicMock(return_value=None)
        self.miner.wait_for_rate_limit_reset = MagicMock(return_value=False)
        self.miner.tokens = ["tok1"]

        rotated = self.miner.handle_rate_limit(mock_response)

        self.assertFalse(rotated)
        self.miner.wait_for_rate_limit_reset.assert_called_once()

