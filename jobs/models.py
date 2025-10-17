from django.db import models
from django.utils import timezone

class Task(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    operation = models.TextField()
    repository = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    date_init = models.DateTimeField(null=True, blank=True)
    date_end = models.DateTimeField(null=True, blank=True)
    date_last_update = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=100)
    status = models.CharField(max_length=50, default='PENDING')
    error = models.TextField(null=True, blank=True)
    error_type = models.CharField(max_length=100, null=True, blank=True)
    token_validation_error = models.BooleanField(default=False)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation} - {self.repository} ({self.task_id})"
