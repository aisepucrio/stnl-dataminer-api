from django_filters import rest_framework as filters
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubIssuePullRequest

class GitHubCommitFilter(filters.FilterSet):
    # Filters for dates
    created_after = filters.DateTimeFilter(field_name='date', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='date', lookup_expr='lte')
    
    # Text filters
    message = filters.CharFilter(lookup_expr='icontains')
    author_name = filters.CharFilter(field_name='author__name', lookup_expr='icontains')
    repository = filters.CharFilter(lookup_expr='iexact')
    
    class Meta:
        model = GitHubCommit
        fields = ['sha', 'repository']

class GitHubIssueFilter(filters.FilterSet):
    # Filters for dates
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Text filters
    title = filters.CharFilter(lookup_expr='icontains')
    creator = filters.CharFilter(lookup_expr='icontains')
    repository = filters.CharFilter(lookup_expr='iexact')
    repository_contains = filters.CharFilter(field_name='repository', lookup_expr='icontains')
    repository_in = filters.CharFilter(method='filter_repository_in')
    state = filters.CharFilter(lookup_expr='iexact')
    
    def filter_repository_in(self, queryset, name, value):
        repositories = [repo.strip() for repo in value.split(',')]
        return queryset.filter(repository__in=repositories)
    
    class Meta:
        model = GitHubIssue
        fields = ['issue_id', 'state', 'repository']

class GitHubPullRequestFilter(filters.FilterSet):
    # Filters for dates
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Text filters
    title = filters.CharFilter(lookup_expr='icontains')
    creator = filters.CharFilter(lookup_expr='icontains')
    repository = filters.CharFilter(lookup_expr='iexact')
    repository_contains = filters.CharFilter(field_name='repository', lookup_expr='icontains')
    repository_in = filters.CharFilter(method='filter_repository_in')
    state = filters.CharFilter(lookup_expr='iexact')
    
    # Filter for labels (JSON field)
    has_label = filters.CharFilter(method='filter_has_label')
    
    def filter_repository_in(self, queryset, name, value):
        repositories = [repo.strip() for repo in value.split(',')]
        return queryset.filter(repository__in=repositories)
    
    class Meta:
        model = GitHubPullRequest
        fields = ['pr_id', 'state', 'repository']

    def filter_has_label(self, queryset, name, value):
        return queryset.filter(labels__contains=[value])

class GitHubBranchFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    repository = filters.CharFilter(field_name='repository', lookup_expr='exact')
    repository_contains = filters.CharFilter(field_name='repository', lookup_expr='icontains')
    repository_in = filters.CharFilter(method='filter_repository_in')
    
    def filter_repository_in(self, queryset, name, value):
        repositories = [repo.strip() for repo in value.split(',')]
        return queryset.filter(repository__in=repositories)
    
    class Meta:
        model = GitHubBranch
        fields = {
            'name': ['icontains'],
            'repository': ['exact'],
            'sha': ['exact']
        }

class GitHubIssuePullRequestFilter(filters.FilterSet):
    # Filters for dates
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Text filters
    title = filters.CharFilter(lookup_expr='icontains')
    creator = filters.CharFilter(lookup_expr='icontains')
    repository = filters.CharFilter(lookup_expr='iexact')
    repository_contains = filters.CharFilter(field_name='repository', lookup_expr='icontains')
    repository_in = filters.CharFilter(method='filter_repository_in')
    state = filters.CharFilter(lookup_expr='iexact')
    data_type = filters.CharFilter(lookup_expr='iexact')
    
    # Filter for labels (JSON field)
    has_label = filters.CharFilter(method='filter_has_label')
    
    def filter_repository_in(self, queryset, name, value):
        repositories = [repo.strip() for repo in value.split(',')]
        return queryset.filter(repository__in=repositories)
    
    def filter_has_label(self, queryset, name, value):
        return queryset.filter(labels__contains=[value])

    class Meta:
        model = GitHubIssuePullRequest
        fields = ['record_id', 'state', 'repository', 'data_type'] 