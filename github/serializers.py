from rest_framework import serializers
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod, GitHubMetadata, GitHubIssuePullRequest

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

class GitHubMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubMetadata
        fields = [
            'repository',
            'owner',
            'organization',
            'stars_count',
            'watchers_count',
            'forks_count',
            'open_issues_count',
            'default_branch',
            'description',
            'html_url',
            'contributors_count',
            'topics',
            'languages',
            'readme',
            'labels_count',
            'created_at',
            'updated_at',
            'is_archived',
            'is_template'
        ]

class GitHubIssuePullRequestSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()
    closed_at_formatted = serializers.SerializerMethodField()
    merged_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = GitHubIssuePullRequest
        fields = '__all__'

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S") if obj.created_at else None

    def get_updated_at_formatted(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M:%S") if obj.updated_at else None

    def get_closed_at_formatted(self, obj):
        return obj.closed_at.strftime("%Y-%m-%d %H:%M:%S") if obj.closed_at else None

    def get_merged_at_formatted(self, obj):
        return obj.merged_at.strftime("%Y-%m-%d %H:%M:%S") if obj.merged_at else None
