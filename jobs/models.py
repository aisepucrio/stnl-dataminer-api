from django.db import models
from django.utils import timezone

class Task(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    operation = models.CharField(max_length=100)
    repository = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='PENDING')
    error = models.TextField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation} - {self.repository} ({self.task_id})"
