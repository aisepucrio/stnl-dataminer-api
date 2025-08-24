from django.urls import path

from .views import *


urlpatterns = [
    # Collect Endpoints
    path('issues/collect/', JiraIssueCollectView.as_view(), name='collect-jira-issues'),
    # Dashboard Endpoints
    path('dashboard/', JiraDashboardView.as_view(), name='dashboard'),
    path('dashboard/graph/', JiraGraphDashboardView.as_view(), name='graph-dashboard'),
    # List Endpoints
    path('issues/', JiraIssueListView.as_view(), name='issues-list'),
    path('projects/', JiraProjectListView.as_view(), name='jira-project-list'),
    path('users/', JiraUserListView.as_view(), name='jira-user-list'),
    path('checklists/', JiraChecklistListView.as_view(), name='jira-checklist-list'),
    path('issue-types/', JiraIssueTypeListView.as_view(), name='jira-issuetype-list'),
    path('sprints/', JiraSprintListView.as_view(), name='jira-sprint-list'),
    path('comments/', JiraCommentListView.as_view(), name='jira-comment-list'),
    path('issue-links/', JiraIssueLinkListView.as_view(), name='jira-issuelink-list'),
    path('commits/', JiraCommitListView.as_view(), name='jira-commit-list'),
    path('activity-logs/', JiraActivityLogListView.as_view(), name='jira-activitylog-list'),
    path('histories/', JiraHistoryListView.as_view(), name='jira-history-list'),
    path('history-items/', JiraHistoryItemListView.as_view(), name='jira-historyitem-list'),
    path('date-range/', JiraProjectDateRangeView.as_view(), name='jira-date-range'),
]
