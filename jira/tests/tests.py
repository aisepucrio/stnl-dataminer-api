# jira/tests/tests.py

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import uuid
from django.utils import timezone

# Importa todos os models e a exceção customizada para os testes
from jira.models import (
    JiraIssue, JiraProject, JiraUser, JiraComment, JiraSprint,
    JiraIssueType, JiraHistory, JiraHistoryItem, JiraCommit,
    JiraChecklist, JiraIssueLink, JiraActivityLog
)
from jira.miner import JiraMiner # Importado para testar a exceção
from jobs.models import Task

class JiraAPITests(APITestCase):
    """
    Suite de testes que cobre os cenários de sucesso ("caminho feliz") e a
    saúde geral de todos os endpoints da API do Jira.
    """

    def setUp(self):
        """
        Cria uma base de dados de teste rica para garantir que todas as rotas de 
        listagem tenham conteúdo para retornar.
        """
        self.user = JiraUser.objects.create(accountId='user-123', displayName='Test User', emailAddress='test@user.com', active=True, timeZone='America/Sao_Paulo', accountType='atlassian')
        self.project = JiraProject.objects.create(id='10001', key='PROJ', name='Test Project', simplified=False, projectTypeKey='software')
        self.issue = JiraIssue.objects.create(issue_id='123', issue_key='PROJ-123', project=self.project, summary='Bug em tela de login', status='To Do', created=timezone.now(), updated=timezone.now(), creator=self.user, reporter=self.user)
        self.issue2 = JiraIssue.objects.create(issue_id='124', issue_key='PROJ-124', project=self.project, summary='Outro bug', status='To Do', created=timezone.now(), updated=timezone.now())
        self.comment = JiraComment.objects.create(issue=self.issue, author=self.user, body="Comentário de teste.", created=timezone.now(), updated=timezone.now())
        self.sprint = JiraSprint.objects.create(id=1, name='Sprint de Teste', state='active', boardId=1)
        self.sprint.issues.add(self.issue)
        self.issue_type = JiraIssueType.objects.create(issue=self.issue, issuetype='Bug')
        self.history = JiraHistory.objects.create(issue=self.issue, author=self.user, created=timezone.now())
        self.history_item = JiraHistoryItem.objects.create(history=self.history, field='status', toString='In Progress')
        self.commit = JiraCommit.objects.create(issue=self.issue, sha='a1b2c3d4e5f6', author='Committer', author_email='c@test.com', message='fix', timestamp=timezone.now())
        self.checklist = JiraChecklist.objects.create(issue=self.issue, checklist={"items": []}, progress="0%", completed=False)
        self.issue_link = JiraIssueLink.objects.create(issue=self.issue, linked_issue=self.issue2, link_type='Blocks', link_direction='outward')
        self.activity_log = JiraActivityLog.objects.create(issue=self.issue, author=self.user, created=timezone.now(), description='Status changed')

    @patch('jira.views.collect.collect_jira_issues_task')
    def test_start_jira_collection_success(self, mock_task):
        """
        [Cenário]: Requisição de coleta bem-sucedida.
        [O Que Testa]: Garante que um payload JSON válido e completo dispara a tarefa Celery.
        [Como Testa]: Envia um POST para 'collect-jira-issues' com a estrutura de 'projects' correta.
        [Resultado Esperado]: A API deve retornar 202 Accepted.
        """
        url = reverse('collect-jira-issues')
        data = {'projects': [{'jira_domain': 'test.atlassian.net','project_key': 'PROJ'}]}
        mock_task.delay.return_value = MagicMock(id=str(uuid.uuid4()))
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.delay.assert_called_once()

    def test_lookup_issues_list_and_content(self):
        """
        [Cenário]: Consulta da lista de issues.
        [O Que Testa]: Garante que a rota funciona e que o contrato da API (estrutura e dados) está correto.
        [Como Testa]: Envia um GET para 'issues-list' e inspeciona o conteúdo da resposta.
        [Resultado Esperado]: Retorna 200 OK e os campos da issue correspondem aos dados do setUp.
        """
        url = reverse('issues-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        first_issue = next(item for item in response.data['results'] if item['issue_id'] == '123')
        self.assertEqual(first_issue['summary'], 'Bug em tela de login')

    def test_all_list_endpoints_return_ok(self):
        """
        [Cenário]: Verificação de "saúde" de todas as rotas de listagem.
        [O Que Testa]: Garante que todas as rotas de listagem estão ativas e retornam uma resposta bem-sucedida.
        [Como Testa]: Itera sobre uma lista de nomes de rotas e faz um GET para cada uma.
        [Resultado Esperado]: Todos os endpoints devem retornar 200 OK.
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
        [Cenário]: Verificação de "saúde" das rotas de dashboard e utilitários.
        [O Que Testa]: Garante que os endpoints que não são de listagem padrão estão ativos.
        [Como Testa]: Itera sobre os nomes das rotas e faz um GET para cada uma.
        [Resultado Esperado]: Todos os endpoints devem retornar 200 OK.
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
    Suite de testes focada na robustez da API de coleta, validando
    diferentes tipos de payloads malformados para garantir que a aplicação
    não quebre e retorne o erro apropriado.
    """
    def setUp(self):
        self.url = reverse('collect-jira-issues')
        self.base_project = {'jira_domain': 'test.atlassian.net', 'project_key': 'PROJ'}

    def test_fails_with_missing_projects_key(self):
        """[Validação]: Falha se a chave 'projects' estiver ausente."""
        data = {'issuetypes': ['Bug']} 
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_fails_with_empty_projects_list(self):
        """[Validação]: Falha se a lista 'projects' estiver vazia."""
        data = {'projects': []} 
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_invalid_projects_type(self):
        """[Validação]: Falha se 'projects' for uma string em vez de uma lista."""
        data = {'projects': "isso não é uma lista"} 
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_missing_keys_in_project_object(self):
        """[Validação]: Falha se um objeto em 'projects' não tiver 'project_key'."""
        data = {'projects': [{'jira_domain': 'test.atlassian.net'}]}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fails_with_invalid_issuetypes_type(self):
        """[Validação]: Falha se 'issuetypes' for uma string em vez de uma lista."""
        data = {'projects': [self.base_project], 'issuetypes': 'Bug'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class JiraTasksTests(APITestCase):
    @patch('jira.tasks.JiraMiner')
    @patch('celery.app.task.Task.request')
    def test_collect_jira_issues_task_logic_success(self, mock_task_request, mock_jira_miner_class):
        """
        [Cenário]: Execução da lógica interna da tarefa de coleta (Sucesso).
        [O Que Testa]: Valida o fluxo da tarefa Celery em um cenário de sucesso.
        [Como Testa]: Chama o método .run() da tarefa diretamente, com mocks.
        [Resultado Esperado]: Um objeto Task é criado, o status é 'SUCCESS' e o JiraMiner é chamado.
        """
        from jira.tasks import collect_jira_issues_task
        mock_task_request.id = str(uuid.uuid4())
        mock_jira_miner_class.return_value.collect_jira_issues.return_value = {'total_issues': 5}
        
        collect_jira_issues_task.run('test.atlassian.net', 'PROJ', ['Bug'], None, None)
        
        task_obj = Task.objects.first()
        self.assertTrue(task_obj)
        self.assertEqual(task_obj.status, 'SUCCESS')
        mock_jira_miner_class.return_value.collect_jira_issues.assert_called_once()

    # O teste 'test_collect_jira_issues_task_handles_token_error' foi removido conforme solicitado.

