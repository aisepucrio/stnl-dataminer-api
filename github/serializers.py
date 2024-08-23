from rest_framework import serializers
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch

class GitHubCommitSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubCommit
        fields = '__all__'

class GitHubIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubIssue
        fields = '__all__'

class GitHubPullRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubPullRequest
        fields = '__all__'

class GitHubBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubBranch
        fields = '__all__'
