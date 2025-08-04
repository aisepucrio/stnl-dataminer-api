from rest_framework import serializers
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod, GitHubMetadata, GitHubIssuePullRequest
from .utils import DateTimeHandler

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
        return DateTimeHandler.format_date(obj.created_at)

    def get_updated_at_formatted(self, obj):
        return DateTimeHandler.format_date(obj.updated_at)

class GitHubPullRequestSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()
    labels_list = serializers.SerializerMethodField()

    class Meta:
        model = GitHubPullRequest
        fields = '__all__'

    def get_created_at_formatted(self, obj):
        return DateTimeHandler.format_date(obj.created_at)

    def get_updated_at_formatted(self, obj):
        return DateTimeHandler.format_date(obj.updated_at)

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
        return DateTimeHandler.format_date(obj.created_at)

    def get_updated_at_formatted(self, obj):
        return DateTimeHandler.format_date(obj.updated_at)

    def get_closed_at_formatted(self, obj):
        return DateTimeHandler.format_date(obj.closed_at)

    def get_merged_at_formatted(self, obj):
        return DateTimeHandler.format_date(obj.merged_at)

class GraphDashboardSerializer(serializers.Serializer):
    repository_id = serializers.IntegerField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    interval = serializers.ChoiceField(
        choices=['day', 'week', 'month'],
        default='day',
        required=False
    )
    
    def validate(self, data):
        """
        Check that start_date is before end_date if both are provided.
        """
        if 'start_date' in data and 'end_date' in data:
            DateTimeHandler.validate_date_range(data['start_date'], data['end_date'])
        return data

class GitHubCollectAllSerializer(serializers.Serializer):
    repositories = serializers.ListField(
        child=serializers.CharField(help_text="Repository name in format owner/repo"),
        help_text="List of repositories to mine"
    )
    start_date = serializers.DateTimeField(required=False, allow_null=True, help_text="Start date for mining (optional)")
    end_date = serializers.DateTimeField(required=False, allow_null=True, help_text="End date for mining (optional)")
    depth = serializers.ChoiceField(choices=['basic', 'complex'], default='basic', help_text="Mining depth (basic or complex)")
    collect_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['commits', 'issues', 'pull_requests', 'branches', 'metadata', 'comments']),
        help_text="List of data types to mine (commits, issues, pull_requests, branches, metadata, comments)"
    )

    def validate_collect_types(self, value):
        if not value:
            raise serializers.ValidationError("At least one data type must be selected for mining")
        return value

    def validate_repositories(self, value):
        if not value:
            raise serializers.ValidationError("At least one repository must be provided for mining")
        return value

    def validate(self, data):
        if 'start_date' in data and 'end_date' in data:
            DateTimeHandler.validate_date_range(data['start_date'], data['end_date'])
        if 'comments' in data.get('collect_types', []):
            data['depth'] = 'complex'
        return data

class ExportDataSerializer(serializers.Serializer):
    table = serializers.ChoiceField(
        choices=[
            'githubcommit',
            'githubissue',
            'githubpullrequest',
            'githubbranch',
            'githubmetadata',
            'githubissuepullrequest'
        ],
        help_text="Table name to export"
    )
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of IDs to export (optional)"
    )
    format = serializers.ChoiceField(
        choices=['json'],
        default='json',
        help_text="Output format (only JSON is supported)"
    )
    data_type = serializers.ChoiceField(
        choices=['issue', 'pull_request'],
        required=False,
        help_text="Filter by data type (issue or pull_request) - only applies to githubissuepullrequest table"
    )
