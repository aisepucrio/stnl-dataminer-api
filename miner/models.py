from django.db import models

class GitHubCommit(models.Model):
    sha = models.CharField(max_length=40)
    message = models.TextField()
    author_name = models.CharField(max_length=100)
    date = models.DateTimeField()

class GitHubIssue(models.Model):
    issue_id = models.IntegerField()
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=20)
    creator = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    comments = models.JSONField(default=list)

class GitHubPullRequest(models.Model):
    pr_id = models.IntegerField()
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=20)
    creator = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    labels = models.JSONField(default=list)
    commits = models.JSONField(default=list)
    comments = models.JSONField(default=list)

class GitHubBranch(models.Model):
    name = models.CharField(max_length=100)
    sha = models.CharField(max_length=40)
