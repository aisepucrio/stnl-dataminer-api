from django.db import models

# Modelo para representar autores e committer dos commits
class GitHubAuthor(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"

# Modelo principal para representar um commit do GitHub
class GitHubCommit(models.Model):
    sha = models.CharField(max_length=40, unique=True)
    message = models.TextField()
    date = models.DateTimeField()
    author = models.ForeignKey(GitHubAuthor, related_name="author_commits", on_delete=models.SET_NULL, null=True)
    committer = models.ForeignKey(GitHubAuthor, related_name="committer_commits", on_delete=models.SET_NULL, null=True)
    insertions = models.IntegerField(default=0)  # Adicionado valor padrão
    deletions = models.IntegerField(default=0)
    files_changed = models.IntegerField(default=0)
    in_main_branch = models.BooleanField(default=False)
    merge = models.BooleanField(default=False)
    dmm_unit_size = models.FloatField(null=True)
    dmm_unit_complexity = models.FloatField(null=True)
    dmm_unit_interfacing = models.FloatField(null=True)

    def __str__(self):
        return f"Commit {self.sha}"

# Modelo para representar um arquivo modificado em um commit específico
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

    def __str__(self):
        return f"File {self.filename} in Commit {self.commit.sha}"


# Modelo para representar um método dentro de um arquivo modificado
class GitHubMethod(models.Model):
    modified_file = models.ForeignKey(GitHubModifiedFile, related_name="methods", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    complexity = models.IntegerField(null=True)
    max_nesting = models.IntegerField(null=True)

    def __str__(self):
        return f"Method {self.name} in File {self.modified_file.filename}"
    

# Modelos para Issues, Pull Requests e Branches, conforme a necessidade

class GitHubIssue(models.Model):
    issue_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=20)
    creator = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    comments = models.JSONField(default=list)

    def __str__(self):
        return f"Issue {self.issue_id} - {self.title}"


class GitHubPullRequest(models.Model):
    pr_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    state = models.CharField(max_length=20)
    creator = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    labels = models.JSONField(default=list)
    commits = models.JSONField(default=list)
    comments = models.JSONField(default=list)

    def __str__(self):
        return f"Pull Request {self.pr_id} - {self.title}"


class GitHubBranch(models.Model):
    name = models.CharField(max_length=100)
    sha = models.CharField(max_length=40)

    def __str__(self):
        return f"Branch {self.name}"
