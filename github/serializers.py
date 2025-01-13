from rest_framework import serializers
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod

class GitHubAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubAuthor
        fields = ['name', 'email']

class GitHubMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubMethod
        fields = ['name', 'complexity', 'max_nesting']

class GitHubModifiedFileSerializer(serializers.ModelSerializer):
    methods = GitHubMethodSerializer(many=True, read_only=True)
    
    class Meta:
        model = GitHubModifiedFile
        fields = ['filename', 'change_type', 'added_lines', 'deleted_lines', 'complexity', 'methods']

class GitHubCommitSerializer(serializers.ModelSerializer):
    author = GitHubAuthorSerializer(read_only=True)
    committer = GitHubAuthorSerializer(read_only=True)
    modified_files = GitHubModifiedFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = GitHubCommit
        fields = '__all__'

class GitHubIssueSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = GitHubIssue
        fields = '__all__'

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def get_updated_at_formatted(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")

class GitHubPullRequestSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()
    labels_list = serializers.SerializerMethodField()

    class Meta:
        model = GitHubPullRequest
        fields = '__all__'

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def get_updated_at_formatted(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    def get_labels_list(self, obj):
        return obj.labels if isinstance(obj.labels, list) else []

class GitHubBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubBranch
        fields = '__all__'
