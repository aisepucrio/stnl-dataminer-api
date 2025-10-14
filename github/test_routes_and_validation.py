from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.utils import timezone
import uuid

from github.models import GitHubMetadata

# Models
from github.models import (
    GitHubMetadata, GitHubCommit, GitHubAuthor, GitHubModifiedFile, GitHubMethod,
    GitHubIssue, GitHubPullRequest, GitHubBranch
)


from jobs.models import Task

class GitHubAPITests(APITestCase):
    """
    Caminho feliz e "saúde" dos endpoints da app GitHub.
    Cria um dataset completo no setUp para que todas as rotas de listagem tenham conteúdo.
    """

    def setUp(self):
        # Metadata (FK raiz para quase tudo)
        self.meta = GitHubMetadata.objects.create(
            repository="openai/gpt",
            owner="openai",
            organization="openai",
            stars_count=4242,
            watchers_count=4242,
            forks_count=100,
            open_issues_count=5,
            default_branch="main",
            description="Test repo",
            html_url="https://github.com/openai/gpt",
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

        # Autores / Commit
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

        # Issue
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

        # Pull Request
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

        # Branch
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
            [Cenário]: Requisição de coleta de commits bem-sucedida.
            [O Que Testa]: ...
            [Como Testa]: ...
            [Resultado Esperado]: ...
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
        [Cenário]: Coleta de commit específico (SHA) bem-sucedida.
        [O Que Testa]: Disparo da task com 'repo_name' e 'commit_sha'.
        [Como Testa]: POST em 'github:commit-collect-by-sha-list'.
        [Resultado Esperado]: 202/200 e task.apply_async chamada 1x.
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
        [Cenário]: Coleta de issues bem-sucedida.
        [O Que Testa]: Disparo da task com 'repo_name' e datas opcionais ISO.
        [Como Testa]: POST em 'github:issue-collect-list'.
        [Resultado Esperado]: 202/200 e task.apply_async chamada 1x.
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
        [Cenário]: Coleta de pull requests bem-sucedida.
        [O Que Testa]: Disparo da task com 'repo_name' e datas opcionais ISO.
        [Como Testa]: POST em 'github:pullrequest-collect-list'.
        [Resultado Esperado]: 202/200 e task.apply_async chamada 1x.
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
        [Cenário]: Coleta de branches bem-sucedida.
        [O Que Testa]: Disparo da task com 'repo_name' top-level.
        [Como Testa]: POST em 'github:branch-collect-list'.
        [Resultado Esperado]: 202/200 e task.apply_async chamada 1x.
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
        [Cenário]: Coleta de metadados de repositório bem-sucedida.
        [O Que Testa]: Disparo da task com 'repo_name' top-level.
        [Como Testa]: POST em 'github:metadata-collect-list'.
        [Resultado Esperado]: 202/200 e task.apply_async chamada 1x.
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
        [Cenário]: Coleta combinada (collect-all) bem-sucedida para múltiplos tipos.
        [O Que Testa]: Disparo encadeado das tasks via chamadas internas do APIClient.
        [Como Testa]: POST em 'github:collect-all-list' com repositories + collect_types.
        [Resultado Esperado]: 202 e cada task.apply_async chamada ao menos 1x.
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

    # ------------------ Validações negativas: COMMITS ------------------
    def test_commit_collect_missing_repo_name_returns_400(self):
        """
        [Cenário]: Falta de 'repo_name'.
        [O Que Testa]: Validação de campo obrigatório.
        [Como Testa]: POST sem 'repo_name'.
        [Resultado Esperado]: 400.
        """
        url = reverse('github:commit-collect-list')
        resp = self.client.post(url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, getattr(resp,'data',resp.content))

    def test_commit_collect_invalid_date_format_returns_400(self):
        """
        [Cenário]: Data em formato inválido / tipo errado.
        [O Que Testa]: parse de datas (ISO) e tipos.
        [Como Testa]: start_date/end_date inválidos.
        [Resultado Esperado]: 400.
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
        [Cenário]: Intervalo de datas invertido.
        [O Que Testa]: Validação de faixa (start <= end).
        [Como Testa]: start_date > end_date.
        [Resultado Esperado]: 400.
        """
        url = reverse('github:commit-collect-list')
        p = {
            'repo_name': self.meta.repository,
            'start_date': '2025-02-01T00:00:00Z',
            'end_date':   '2025-01-01T00:00:00Z',
        }
        r = self.client.post(url, p, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

    # ------------------ Validações negativas: ISSUES / PRs / BRANCHES / METADATA ------------------
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

    # ------------------ Validações negativas: COMMITS por SHA ------------------
    def test_commit_by_sha_missing_fields_returns_400(self):
        url = reverse('github:commit-collect-by-sha-list')

        # faltando repo_name
        r = self.client.post(url, {'commit_sha': 'a'*40}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))

        # faltando commit_sha
        r = self.client.post(url, {'repo_name': self.meta.repository}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, getattr(r,'data',r.content))


from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from django.utils import timezone
import uuid

from jobs.models import Task
from github.models import GitHubMetadata

class GitHubTasksTests(APITestCase):
    """
    Testes de lógica interna das tasks Celery (sem bater em Redis/worker).
    Sem testes de token, só fluxo e persistência de Task.
    """

    def setUp(self):
        self.meta = GitHubMetadata.objects.create(
            repository="openai/gpt",
            owner="openai",
            organization="openai",
            stars_count=1, watchers_count=1, forks_count=0, open_issues_count=0,
            default_branch="main", description="repo", html_url="https://github.com/openai/gpt",
            contributors_count=1, topics=[], languages={"Python": 1}, readme="",
            labels_count=0, github_created_at=timezone.now(), github_updated_at=timezone.now(),
            is_archived=False, is_template=False, used_by_count=0, releases_count=0, time_mined=timezone.now(),
        )

