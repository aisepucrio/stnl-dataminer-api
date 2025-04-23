from django.db import models
from django.utils.timezone import now

class JiraIssue(models.Model):
    issue_id = models.CharField(max_length=100, unique=True, primary_key=True)
    issue_key = models.CharField(max_length=100)
    issuetype = models.CharField(max_length=100)
    project = models.CharField(max_length=100)
    priority = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50)
    assignee = models.CharField(max_length=100, null=True, blank=True)
    creator = models.CharField(max_length=100)
    created = models.DateTimeField()
    updated = models.DateTimeField()
    issuetype = models.CharField(max_length=100)
    issuetype_description = models.TextField(null=True, blank=True)
    summary = models.TextField()
    description = models.TextField(null=True, blank=True)
    all_fields = models.JSONField(null=True, blank=True)
    time_mined = models.DateTimeField(default=now)
    commits = models.JSONField(max_length=50, null=True, blank=True)
    comments = models.JSONField(default=list, null=True, blank=True)
    history = models.JSONField(default=list, null=True, blank=True, help_text="Histórico de alterações da issue")
    activity_log = models.JSONField(default=list, null=True, blank=True, help_text="Registro de atividades da issue")
    checklist = models.JSONField(default=list, null=True, blank=True, help_text="Checklist com informações de datas")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['issue_id', 'project'], name='unique_issue')
        ]
        # Definindo uma chave composta com `issue_id` e `project`
        unique_together = (('issue_id', 'project'),)

    def __str__(self):
        return f"{self.issue_key} - {self.summary}"