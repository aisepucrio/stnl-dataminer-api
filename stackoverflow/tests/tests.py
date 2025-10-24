from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import uuid

# Imports the models needed to create test data
from stackoverflow.models import StackUser, StackQuestion, StackTag
from jobs.models import Task

class StackOverflowAPITests(APITestCase):
    """
    Test suite for the Stack Overflow API endpoints, covering
    data collection and question lookup.
    """

    def setUp(self):
        """
        Creates sample data in the test database so that lookup routes
        have data to return and validate.
        """
        self.user = StackUser.objects.create(user_id=1, display_name='Test User')
        self.tag = StackTag.objects.create(name='django')
        self.question = StackQuestion.objects.create(
            question_id=101,
            title='How to test in Django?',
            owner=self.user,
            score=10
        )
        self.question.tags.add(self.tag)

    # Tests for the Collection Route (/collect/)

    @patch('stackoverflow.views.collect.chain')
    def test_start_collection_job_success(self, mock_celery_chain):
        """
        [Scenario]: Successful collection request.
        [What It Tests]: Ensures that a valid JSON payload triggers the Celery task chain.
        [How It Tests]: Sends a POST to 'stackoverflow-collect-list' with 'options' and dates.
        [Expected Result]: The API should return 202 Accepted and the Celery task should be called.
        """
        # Arrange: Prepare URL and data
        url = reverse('stackoverflow-collect-list')
        data = {
            "options": ["collect_questions"],
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
            "tags": "python"
        }
        
        # Configure mock to prevent the test from hanging when serializing the response
        mock_chain_result = MagicMock()
        mock_chain_result.id = str(uuid.uuid4())
        mock_celery_chain.return_value.apply_async.return_value = mock_chain_result

        # Act: Simulate the request
        response = self.client.post(url, data, format='json')

        # Assert: Verify the result
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], mock_chain_result.id)
        mock_celery_chain.return_value.apply_async.assert_called_once()

    def test_start_collection_job_bad_request(self):
        """
        [Scenario]: Collection request with missing data.
        [What It Tests]: API validation against incomplete payloads.
        [How It Tests]: Sends a POST without the 'options' key.
        [Expected Result]: The API should reject the request with 400 Bad Request.
        """
        url = reverse('stackoverflow-collect-list')
        data = {"start_date": "2025-01-01"}  # Missing 'options'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Tests for Lookup Routes (/questions/)

    def test_lookup_questions_list_and_content(self):
        """
        [Scenario]: Query the list of questions.
        [What It Tests]: Ensures that the listing route works and that the API contract (structure and data) is correct.
        [How It Tests]: Sends a GET to 'stackoverflow-question-list' and inspects the content.
        [Expected Result]: Returns 200 OK, a list with the question created in setUp, and fields matching the data.
        """
        url = reverse('stackoverflow-question-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        question_data = response.data['results'][0]
        self.assertEqual(question_data['title'], 'How to test in Django?')
        self.assertEqual(question_data['score'], 10)
        self.assertEqual(question_data['owner']['display_name'], 'Test User')

    def test_lookup_question_detail(self):
        """
        [Scenario]: Query a specific question.
        [What It Tests]: Ensures that the object detail route works.
        [How It Tests]: Sends a GET to 'stackoverflow-question-detail' with the question PK.
        [Expected Result]: Returns 200 OK and the data of the specific question.
        """
        url = reverse('stackoverflow-question-detail', kwargs={'pk': self.question.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'How to test in Django?')
        self.assertEqual(response.data['question_id'], self.question.question_id)

class StackOverflowTasksTests(APITestCase):
    """
    Unit test suite for Stack Overflow Celery tasks.
    """

    @patch('stackoverflow.tasks.fetch_questions')
    @patch('celery.app.task.Task.request')
    def test_collect_questions_task_logic(self, mock_task_request, mock_fetch_questions):
        """
        [Scenario]: Execution of the internal logic of the collection task.
        [What It Tests]: Validates the task flow in isolation, without network I/O.
        [How It Tests]: Calls the .run() method of the task directly, with mocks.
        [Expected Result]: A Task object is created, status is 'COMPLETED', and the 'fetch_questions' miner is called.
        """
        from stackoverflow.tasks import collect_questions_task
        mock_task_request.id = str(uuid.uuid4())
        
        collect_questions_task.run(start_date="2025-01-01", end_date="2025-01-02", tags="django")
        
        task_obj = Task.objects.first()
        self.assertTrue(task_obj)
        self.assertEqual(task_obj.status, 'COMPLETED')
        self.assertEqual(task_obj.repository, "Stack Overflow")
        mock_fetch_questions.assert_called_once()
