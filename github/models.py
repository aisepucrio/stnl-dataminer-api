from django.db import models
class GitHubAuthor(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)

    class Meta:
        unique_together = ['name', 'email']

    def __str__(self):
        return f"{self.name} <{self.email}>"

class GitHubCommit(models.Model):
    repository = models.CharField(max_length=255, db_index=True, default='')
    sha = models.CharField(max_length=40, unique=True)
    message = models.TextField()
    date = models.DateTimeField()
    author = models.ForeignKey(GitHubAuthor, related_name="author_commits", on_delete=models.SET_NULL, null=True)
    committer = models.ForeignKey(GitHubAuthor, related_name="committer_commits", on_delete=models.SET_NULL, null=True)
    insertions = models.IntegerField(default=0)  
    deletions = models.IntegerField(default=0)
    files_changed = models.IntegerField(default=0)
    in_main_branch = models.BooleanField(default=False)
    merge = models.BooleanField(default=False)
    dmm_unit_size = models.FloatField(null=True)
    dmm_unit_complexity = models.FloatField(null=True)
    dmm_unit_interfacing = models.FloatField(null=True)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")


    def __str__(self):
        return f"Commit {self.sha}"

class GitHubModifiedFile(models.Model):
    commit = models.ForeignKey(GitHubCommit, related_name="modified_files", on_delete=models.CASCADE)
    old_path = models.TextField(null=True)
    new_path = models.TextField(null=True)
    filename = models.TextField()
    change_type = models.CharField(max_length=20)
    diff = models.TextField(null=True)  
    added_lines = models.IntegerField()
    deleted_lines = models.IntegerField()
    complexity = models.IntegerField(null=True)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")


    def __str__(self):
        return f"File {self.filename} in Commit {self.commit.sha}"

class GitHubMethod(models.Model):
    modified_file = models.ForeignKey(GitHubModifiedFile, related_name="methods", on_delete=models.CASCADE)
    name = models.TextField()
    complexity = models.IntegerField(null=True)
    max_nesting = models.IntegerField(null=True)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")

    def __str__(self):
        return f"Method {self.name} in File {self.modified_file.filename}"

class GitHubIssue(models.Model):
    repository = models.CharField(max_length=255, db_index=True, default='')
    issue_id = models.BigIntegerField()
    number = models.IntegerField(null=True)
    title = models.TextField()
    state = models.CharField(max_length=20)
    creator = models.CharField(max_length=100)
    assignees = models.JSONField(default=list)
    labels = models.JSONField(default=list)
    milestone = models.CharField(max_length=255, null=True, blank=True)
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    comments = models.JSONField(default=list)
    timeline_events = models.JSONField(default=list)
    is_pull_request = models.BooleanField(default=False)
    author_association = models.CharField(max_length=50, null=True, blank=True)
    reactions = models.JSONField(default=dict)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")

    class Meta:
        indexes = [
            models.Index(fields=['repository', 'issue_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at'])
        ]

    def __str__(self):
        return f"Issue {self.issue_id} - {self.title}"

class GitHubPullRequest(models.Model):
    pr_id = models.BigIntegerField(primary_key=True)
    repository = models.CharField(max_length=255)
    number = models.IntegerField(null=True)
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=50)
    creator = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True)
    merged_at = models.DateTimeField(null=True)
    labels = models.JSONField(default=list)
    commits = models.JSONField(default=list)
    comments = models.JSONField(default=list)
    body = models.TextField(null=True, blank=True)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")

    class Meta:
        db_table = 'github_pull_requests'

    def __str__(self):
        return f"Pull Request {self.pr_id} - {self.title}"

class GitHubBranch(models.Model):
    repository = models.CharField(max_length=255, db_index=True, default='')
    name = models.CharField(max_length=500)
    sha = models.CharField(max_length=40)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")

    def __str__(self):
        return f"Branch {self.name}"

class GitHubMetadata(models.Model):
    repository = models.CharField(max_length=255, db_index=True)
    owner = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, null=True)
    stars_count = models.IntegerField(default=0)
    watchers_count = models.IntegerField(default=0)
    forks_count = models.IntegerField(default=0)
    open_issues_count = models.IntegerField(default=0)
    default_branch = models.CharField(max_length=255, default='main')
    description = models.TextField(null=True)
    html_url = models.URLField()
    contributors_count = models.IntegerField(null=True)
    topics = models.JSONField(null=True)
    languages = models.JSONField(null=True)
    readme = models.TextField(null=True)
    labels_count = models.IntegerField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    last_sync = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    is_template = models.BooleanField(default=False)
    used_by_count = models.IntegerField(default=0)
    releases_count = models.IntegerField(default=0)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")
    
    class Meta:
        indexes = [
            models.Index(fields=['repository']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at'])
        ]

    def __str__(self):
        return f"Metadata for {self.repository}"

class GitHubIssuePullRequest(models.Model):
    repository = models.CharField(max_length=255, db_index=True, default='')
    record_id = models.BigIntegerField(unique=True)
    number = models.IntegerField(null=True)
    title = models.TextField()
    state = models.CharField(max_length=20)
    creator = models.CharField(max_length=100)
    assignees = models.JSONField(default=list)
    labels = models.JSONField(default=list)
    milestone = models.CharField(max_length=255, null=True, blank=True)
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    comments = models.JSONField(default=list)
    timeline_events = models.JSONField(default=list)
    merged_at = models.DateTimeField(null=True, blank=True)
    commits = models.JSONField(default=list)
    is_pull_request = models.BooleanField(default=False)
    author_association = models.CharField(max_length=50, null=True, blank=True)
    reactions = models.JSONField(default=dict)
    tipo = models.CharField(max_length=20)
    time_mined = models.DateTimeField(null=True, help_text="Data e hora da mineração")

    class Meta:
        indexes = [
            models.Index(fields=['repository', 'record_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at'])
        ]

    def __str__(self):
        return f"{self.tipo.capitalize()} {self.record_id} - {self.title}"
