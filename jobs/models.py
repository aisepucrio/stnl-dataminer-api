from django.db import models
from django.utils import timezone

class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField()  
    depends_on = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependents')

    def __str__(self):
        return f"Task {self.id} - {self.status}"

    def cancel(self):
        self.status = self.Status.FAILED
        self.save()

    def mark_in_progress(self):
        self.status = self.Status.IN_PROGRESS
        self.save()

    def complete(self):
        self.status = self.Status.COMPLETED
        self.save()
