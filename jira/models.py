from django.db import models
from django.contrib.auth.models import User

class JiraCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    jira_email = models.EmailField()
    jira_api_token = models.CharField(max_length=100)

    def __str__(self):
        return f"Credentials for {self.user.username}"

class JiraIssue(models.Model):
    issue_id = models.CharField(max_length=100, unique=True)
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
    custom_fields = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.key} - {self.summary}"