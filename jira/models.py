from django.db import models

class JiraIssueType(models.Model):
    issuetype_id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['issuetype_id', 'domain'], name='unique_issuetype')
        ]
        # Definindo uma chave composta com `issuetype_id` e `domain`
        unique_together = (('issuetype_id', 'domain'),) 

    def __str__(self):
        return f"{self.domain}: {self.name} ({self.id})"

class JiraIssue(models.Model):
    issue_id = models.CharField(max_length=100, unique=True, primary_key=True)
    key = models.CharField(max_length=100)
    issuetype = models.CharField(max_length=100)
    summary = models.TextField()
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()
    status = models.CharField(max_length=50)
    priority = models.CharField(max_length=50, null=True, blank=True)
    project = models.CharField(max_length=100)
    creator = models.CharField(max_length=100)
    assignee = models.CharField(max_length=100, null=True, blank=True)
    reporter = models.CharField(max_length=100, null=True, blank=True)
    all_fields = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['issue_id', 'project'], name='unique_issue')
        ]
        # Definindo uma chave composta com `issue_id` e `project`
        unique_together = (('issue_id', 'project'),)

    def __str__(self):
        return f"{self.key} - {self.summary}"