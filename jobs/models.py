from django.db import models
from django.utils import timezone
from utils.models import Repository

class Task(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    operation = models.TextField()
    repository = models.ForeignKey(Repository, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    repository_name = models.CharField(max_length=255, default='', help_text="Nome do repositório para casos onde Repository não existe")
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='PENDING')
    error = models.TextField(null=True, blank=True)
    error_type = models.CharField(max_length=100, null=True, blank=True)
    token_validation_error = models.BooleanField(default=False)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        repo_name = self.repository.full_name if self.repository else self.repository_name
        return f"{self.operation} - {repo_name} ({self.task_id})"
