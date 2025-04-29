from django_filters import rest_framework as filters
from .models import JiraIssue

class JiraIssueFilter(filters.FilterSet):
    # Date filter
    created_after = filters.DateTimeFilter(field_name='created', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated', lookup_expr='lte')
    
    # Text filter
    summary = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    creator = filters.CharFilter(lookup_expr='icontains')
    assignee = filters.CharFilter(lookup_expr='icontains')
    status = filters.CharFilter(lookup_expr='iexact')
    project = filters.CharFilter(lookup_expr='iexact')
    priority = filters.CharFilter(lookup_expr='iexact')
    issuetype = filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = JiraIssue
        fields = ['issue_id', 'project', 'status', 'priority', 'issuetype']
