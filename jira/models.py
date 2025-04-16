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
    comments = models.JSONField(null=True, blank=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['issue_id', 'project'], name='unique_issue')
        ]
        # Definindo uma chave composta com `issue_id` e `project`
        unique_together = (('issue_id', 'project'),)

    def __str__(self):
        return f"{self.key} - {self.summary}"
    
class Sprint(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    goal = models.TextField(null=True, blank=True)

    # Relacionamento M2M com JiraIssue
    issues = models.ManyToManyField(JiraIssue, related_name='sprints')

    def __str__(self):
        return f"Sprint: {self.name}"
