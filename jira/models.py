from django.db import models
from django.utils.timezone import now


class JiraIssue(models.Model):
    issue_id = models.CharField(max_length=100, primary_key=True)
    issue_key = models.CharField(max_length=100)
    project = models.ForeignKey('JiraProject', on_delete=models.CASCADE)
    created = models.DateTimeField()
    updated = models.DateTimeField()
    time_mined = models.DateTimeField(default=now)
    status = models.CharField(max_length=50)
    priority = models.CharField(max_length=50, null=True, blank=True)
    assignee = models.ForeignKey('JiraUser', on_delete=models.SET_NULL, related_name='assigned_issues', null=True, blank=True)
    creator = models.ForeignKey('JiraUser', on_delete=models.SET_NULL, related_name='created_issues', null=True)
    reporter = models.ForeignKey('JiraUser', on_delete=models.SET_NULL, related_name='reported_issues', null=True)
    summary = models.TextField()
    description = models.TextField(null=True, blank=True)
    duedate = models.DateTimeField(null=True, blank=True)
    timeoriginalestimate = models.IntegerField(null=True, blank=True)
    timeestimate = models.IntegerField(null=True, blank=True)
    timespent = models.IntegerField(null=True, blank=True)
    parent_issue = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.issue_key} - {self.summary}"

class JiraProject(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    key = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    simplified = models.BooleanField()
    projectTypeKey = models.CharField(max_length=50)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class JiraUser(models.Model):
    accountId = models.CharField(max_length=100, primary_key=True)
    displayName = models.CharField(max_length=255)
    emailAddress = models.EmailField()
    active = models.BooleanField()
    timeZone = models.CharField(max_length=100)
    accountType = models.CharField(max_length=50)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.displayName

class JiraComment(models.Model):
    issue = models.ForeignKey(JiraIssue, on_delete=models.CASCADE)
    author = models.CharField(max_length=100)
    body = models.TextField()
    created = models.DateTimeField()
    updated = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

class JiraChecklist(models.Model):
    issue = models.ForeignKey(JiraIssue, on_delete=models.CASCADE)
    checklist = models.JSONField()
    progress = models.CharField(max_length=50)
    completed = models.BooleanField()
    updated_at = models.DateTimeField(auto_now=True)

class JiraIssueType(models.Model):
    issue = models.OneToOneField(JiraIssue, on_delete=models.CASCADE)
    issuetype = models.CharField(max_length=100)
    issuetype_description = models.TextField(blank=True, null=True)
    hierarchyLevel = models.IntegerField(default=0)
    subtask = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

class JiraSprint(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    goal = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=50)
    boardId = models.BigIntegerField()
    startDate = models.DateTimeField(null=True, blank=True)
    endDate = models.DateTimeField(null=True, blank=True)
    completeDate = models.DateTimeField(null=True, blank=True)
    issues = models.ManyToManyField('JiraIssue', related_name='sprints')
    updated_at = models.DateTimeField(auto_now=True)

class JiraIssueLink(models.Model):
    issue = models.ForeignKey(JiraIssue, related_name='issue_links', on_delete=models.CASCADE)
    linked_issue = models.ForeignKey(JiraIssue, related_name='linked_to', on_delete=models.CASCADE)
    link_type = models.CharField(max_length=50)
    link_direction = models.CharField(max_length=50)
    updated_at = models.DateTimeField(auto_now=True)

class JiraCommit(models.Model):
    issue = models.ForeignKey(JiraIssue, on_delete=models.CASCADE)
    sha = models.CharField(max_length=40)
    author = models.CharField(max_length=255)
    author_email = models.EmailField()
    message = models.TextField()
    timestamp = models.DateTimeField()
    repository_id = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

class JiraActivityLog(models.Model):
    issue = models.ForeignKey(JiraIssue, on_delete=models.CASCADE)
    to_value = models.CharField(max_length=100, null=True, blank=True)
    from_value = models.CharField(max_length=100, null=True, blank=True)  
    author = models.CharField(max_length=100)
    created = models.DateTimeField()
    description = models.CharField(max_length=300)
    updated_at = models.DateTimeField(auto_now=True)

class JiraHistory(models.Model):
    issue = models.ForeignKey(JiraIssue, on_delete=models.CASCADE)
    author = models.CharField(max_length=100)
    created = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

class JiraHistoryItem(models.Model):
    history = models.ForeignKey(JiraHistory, on_delete=models.CASCADE)
    field = models.CharField(max_length=100)
    fieldtype = models.CharField(max_length=50)
    from_value = models.CharField(max_length=255, null=True, blank=True)
    to_value = models.CharField(max_length=255, null=True, blank=True)
    fromString = models.TextField(null=True, blank=True)
    toString = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)