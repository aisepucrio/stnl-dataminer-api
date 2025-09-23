from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import uuid

# Importa os models necessários para criar dados de teste
from stackoverflow.models import StackUser, StackQuestion, StackTag
from jobs.models import Task

class StackOverflowAPITests(APITestCase):
    """
    Suite de testes para os endpoints da API do Stack Overflow, cobrindo
    a coleta de dados e a consulta de perguntas.
    """

    def setUp(self):
        """
        Cria dados de exemplo no banco de dados de teste para que as rotas
        de consulta (lookup) tenham o que retornar e validar.
        """
        self.user = StackUser.objects.create(user_id=1, display_name='Test User')
        self.tag = StackTag.objects.create(name='django')
        self.question = StackQuestion.objects.create(
            question_id=101,
            title='Como testar no Django?',
            owner=self.user,
            score=10
        )
        self.question.tags.add(self.tag)

    # --- Testes para a Rota de Coleta (/collect/) ---

    @patch('stackoverflow.views.collect.chain')
    def test_start_collection_job_success(self, mock_celery_chain):
        """
        [Cenário]: Requisição de coleta bem-sucedida.
        [O Que Testa]: Garante que um payload JSON válido dispara a cadeia de tarefas do Celery.
        [Como Testa]: Envia um POST para 'stackoverflow-collect-list' com 'options' e datas.
        [Resultado Esperado]: A API deve retornar 202 Accepted e a tarefa Celery deve ser chamada.
        """
        # Arrange: Prepara a URL e os dados
        url = reverse('stackoverflow-collect-list')
        data = {
            "options": ["collect_questions"],
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
            "tags": "python"
        }
        
        # Configura o mock para evitar que o teste trave ao serializar a resposta
        mock_chain_result = MagicMock()
        mock_chain_result.id = str(uuid.uuid4())
        mock_celery_chain.return_value.apply_async.return_value = mock_chain_result

        # Act: Simula a requisição
        response = self.client.post(url, data, format='json')

        # Assert: Verifica o resultado
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], mock_chain_result.id)
        mock_celery_chain.return_value.apply_async.assert_called_once()

    def test_start_collection_job_bad_request(self):
        """
        [Cenário]: Requisição de coleta com dados faltando.
        [O Que Testa]: A validação da API contra payloads incompletos.
        [Como Testa]: Envia um POST sem a chave 'options'.
        [Resultado Esperado]: A API deve rejeitar a requisição com 400 Bad Request.
        """
        url = reverse('stackoverflow-collect-list')
        data = {"start_date": "2025-01-01"} # Faltando 'options'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Testes para as Rotas de Consulta (/questions/) ---

    def test_lookup_questions_list_and_content(self):
        """
        [Cenário]: Consulta da lista de perguntas.
        [O Que Testa]: Garante que a rota de listagem funciona e que o contrato da API (estrutura e dados) está correto.
        [Como Testa]: Envia um GET para 'stackoverflow-question-list' e inspeciona o conteúdo.
        [Resultado Esperado]: Retorna 200 OK, uma lista com a pergunta criada no setUp, e os campos correspondem aos dados.
        """
        url = reverse('stackoverflow-question-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        question_data = response.data['results'][0]
        self.assertEqual(question_data['title'], 'Como testar no Django?')
        self.assertEqual(question_data['score'], 10)
        self.assertEqual(question_data['owner']['display_name'], 'Test User')

    def test_lookup_question_detail(self):
        """
        [Cenário]: Consulta de uma pergunta específica.
        [O Que Testa]: Garante que a rota de detalhe de um objeto funciona.
        [Como Testa]: Envia um GET para 'stackoverflow-question-detail' com a PK da pergunta.
        [Resultado Esperado]: Retorna 200 OK e os dados da pergunta específica.
        """
        url = reverse('stackoverflow-question-detail', kwargs={'pk': self.question.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Como testar no Django?')
        self.assertEqual(response.data['question_id'], self.question.question_id)

class StackOverflowTasksTests(APITestCase):
    """
    Suite de testes unitários para as tarefas Celery do Stack Overflow.
    """

    @patch('stackoverflow.tasks.fetch_questions')
    @patch('celery.app.task.Task.request')
    def test_collect_questions_task_logic(self, mock_task_request, mock_fetch_questions):
        """
        [Cenário]: Execução da lógica interna da tarefa de coleta.
        [O Que Testa]: Valida o fluxo da tarefa de forma isolada, sem I/O de rede.
        [Como Testa]: Chama o método .run() da tarefa diretamente, com mocks.
        [Resultado Esperado]: Um objeto Task é criado, o status é 'COMPLETED' e o miner 'fetch_questions' é chamado.
        """
        from stackoverflow.tasks import collect_questions_task
        mock_task_request.id = str(uuid.uuid4())
        
        collect_questions_task.run(start_date="2025-01-01", end_date="2025-01-02", tags="django")
        
        task_obj = Task.objects.first()
        self.assertTrue(task_obj)
        self.assertEqual(task_obj.status, 'COMPLETED')
        self.assertEqual(task_obj.repository, "Stack Overflow")
        mock_fetch_questions.assert_called_once()