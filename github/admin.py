from django.contrib import admin
from .models import (
    GitHubAuthor, GitHubCommit, GitHubModifiedFile, GitHubMethod,
    GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubMetadata,
    GitHubIssuePullRequest
)

# Register your models here.
admin.site.register(GitHubAuthor)
admin.site.register(GitHubCommit)
admin.site.register(GitHubModifiedFile)
admin.site.register(GitHubMethod)
admin.site.register(GitHubIssue)
admin.site.register(GitHubPullRequest)
admin.site.register(GitHubBranch)
admin.site.register(GitHubMetadata)
admin.site.register(GitHubIssuePullRequest)
