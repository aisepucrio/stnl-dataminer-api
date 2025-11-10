from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import uuid

from stackoverflow.models import StackUser, StackQuestion, StackTag
from jobs.models import Task


# =============================================================================
# Stack Overflow API Tests
# =============================================================================
class StackOverflowAPITests(APITestCase):
    """Integration tests for Stack Overflow API endpoints."""

    def setUp(self):
        """Create initial test data."""
        self.user = StackUser.objects.create(user_id=1, display_name="Test User")
        self.tag = StackTag.objects.create(name="django")
        self.question = StackQuestion.objects.create(
            question_id=101,
            title="How to test in Django?",
            owner=self.user,
            score=10,
        )
        self.question.tags.add(self.tag)

    @patch("stackoverflow.views.collect.chain")
    def test_start_collection_job_success(self, mock_celery_chain):
        """Should start a collection task and return task ID."""
        # Arrange
        url = reverse("stackoverflow-collect-list")
        data = {
            "options": ["collect_questions"],
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
            "tags": "python",
        }
        mock_chain_result = MagicMock()
        mock_chain_result.id = str(uuid.uuid4())
        mock_celery_chain.return_value.apply_async.return_value = mock_chain_result

        # Act
        response = self.client.post(url, data, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["task_id"], mock_chain_result.id)
        mock_celery_chain.return_value.apply_async.assert_called_once()

    def test_start_collection_job_missing_options(self):
        """Should return 400 when 'options' is missing."""
        # Arrange
        url = reverse("stackoverflow-collect-list")
        data = {"start_date": "2025-01-01"}

        # Act
        response = self.client.post(url, data, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_collection_job_invalid_type(self):
        """Should return 400 when 'options' is not a list."""
        # Arrange
        url = reverse("stackoverflow-collect-list")
        data = {"options": "not a list", "start_date": "2025-01-01"}

        # Act
        response = self.client.post(url, data, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("stackoverflow.views.collect.chain")
    def test_start_collection_job_celery_failure(self, mock_celery_chain):
        """Should handle Celery failure gracefully with 400 response."""
        # Arrange
        url = reverse("stackoverflow-collect-list")
        data = {"options": ["collect_questions"], "tags": "django"}
        mock_celery_chain.return_value.apply_async.side_effect = Exception("Celery error")

        # Act
        response = self.client.post(url, data, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lookup_questions_list_and_content(self):
        """Should return the list of questions with valid data."""
        # Arrange
        url = reverse("stackoverflow-question-list")

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        question = response.data["results"][0]
        self.assertEqual(question["title"], "How to test in Django?")
        self.assertEqual(question["owner"]["display_name"], "Test User")

    def test_lookup_question_detail(self):
        """Should return details of a specific question."""
        # Arrange
        url = reverse("stackoverflow-question-detail", kwargs={"pk": self.question.pk})

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["question_id"], self.question.question_id)

    def test_lookup_question_not_found(self):
        """Should return 404 for non-existent question."""
        # Arrange
        url = reverse("stackoverflow-question-detail", kwargs={"pk": 9999})

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# Celery Task Tests
# =============================================================================
class StackOverflowTasksTests(APITestCase):
    """Unit tests for Stack Overflow Celery task logic."""

    @patch("stackoverflow.tasks.fetch_questions")
    @patch("celery.app.task.Task.request")
    def test_collect_questions_task_success(self, mock_task_request, mock_fetch_questions):
        """Should successfully complete question collection."""
        # Arrange
        from stackoverflow.tasks import collect_questions_task
        mock_task_request.id = str(uuid.uuid4())
        mock_fetch_questions.return_value = {"total": 5}

        # Act
        result = collect_questions_task.run(
            start_date="2025-01-01", end_date="2025-01-02", tags="django"
        )

        # Assert
        task_obj = Task.objects.first()
        self.assertTrue(task_obj)
        self.assertEqual(task_obj.status, "COMPLETED")
        self.assertIn("success", result["status"])
        mock_fetch_questions.assert_called_once()

    @patch("stackoverflow.tasks.fetch_questions", side_effect=Exception("Network error"))
    @patch("celery.app.task.Task.request")
    def test_collect_questions_task_generic_failure(self, mock_task_request, _):
        """Should record failure and return UNEXPECTED_EXCEPTION code."""
        # Arrange
        from stackoverflow.tasks import collect_questions_task
        mock_task_request.id = str(uuid.uuid4())

        # Act
        result = collect_questions_task.run(
            start_date="2025-01-01", end_date="2025-01-02", tags="django"
        )

        # Assert
        task_obj = Task.objects.first()
        self.assertEqual(task_obj.status, "FAILURE")
        self.assertIn("Network error", task_obj.error)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "UNEXPECTED_EXCEPTION")

    @patch("stackoverflow.tasks.fetch_questions", side_effect=Exception("Invalid Stack token"))
    @patch("celery.app.task.Task.request")
    def test_collect_questions_task_invalid_token(self, mock_task_request, _):
        """Should detect invalid token and mark task with NO_VALID_STACK_TOKEN."""
        # Arrange
        from stackoverflow.tasks import collect_questions_task
        mock_task_request.id = str(uuid.uuid4())

        # Act
        result = collect_questions_task.run(
            start_date="2025-01-01", end_date="2025-01-02", tags="django"
        )

        # Assert
        task_obj = Task.objects.first()
        self.assertEqual(task_obj.status, "FAILURE")
        self.assertEqual(task_obj.error_type, "NO_VALID_STACK_TOKEN")
        self.assertIn("Invalid Stack token", task_obj.error)
        self.assertEqual(result["code"], "NO_VALID_STACK_TOKEN")

    @patch("stackoverflow.tasks.fetch_questions", side_effect=Exception("Invalid API key"))
    @patch("celery.app.task.Task.request")
    def test_collect_questions_task_invalid_credentials(self, mock_task_request, _):
        """Should detect invalid credentials and mark task with INVALID_API_CREDENTIALS."""
        # Arrange
        from stackoverflow.tasks import collect_questions_task
        mock_task_request.id = str(uuid.uuid4())

        # Act
        result = collect_questions_task.run(
            start_date="2025-01-01", end_date="2025-01-02", tags="django"
        )

        # Assert
        task_obj = Task.objects.first()
        self.assertEqual(task_obj.status, "FAILURE")
        self.assertEqual(task_obj.error_type, "INVALID_API_CREDENTIALS")
        self.assertIn("Invalid API key", task_obj.error)
        self.assertEqual(result["code"], "INVALID_API_CREDENTIALS")

    @patch("stackoverflow.tasks.fetch_questions")
    @patch("celery.app.task.Task.request")
    def test_collect_questions_task_reuse_existing_task(self, mock_task_request, mock_fetch_questions):
        """Should reuse existing Task instance when task_pk is provided."""
        # Arrange
        from stackoverflow.tasks import collect_questions_task
        existing_task = Task.objects.create(status="PENDING", repository="Stack Overflow")
        mock_task_request.id = str(uuid.uuid4())

        # Act
        collect_questions_task.run(
            start_date="2025-01-01", end_date="2025-01-02", tags="django", task_pk=existing_task.pk
        )

        # Assert
        self.assertEqual(Task.objects.count(), 1)
        mock_fetch_questions.assert_called_once()

    @patch("stackoverflow.tasks.fetch_questions")
    def test_collect_questions_task_without_request_id(self, mock_fetch_questions):
        """Should auto-generate task_id when request ID is missing."""
        # Arrange
        from stackoverflow.tasks import collect_questions_task

        # Act
        collect_questions_task.run(start_date="2025-01-01", end_date="2025-01-02", tags="python")

        # Assert
        task_obj = Task.objects.first()
        self.assertTrue(task_obj)
        self.assertEqual(task_obj.status, "COMPLETED")
