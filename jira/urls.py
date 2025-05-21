from django.urls import path
from .views import JiraIssueCollectView, JiraIssueListView, JiraIssueDetailView, JiraDashboardView, JiraGraphDashboardView

urlpatterns = [
    path('issues/collect/', JiraIssueCollectView.as_view(), name='collect-jira-issues'),
    path('issues/', JiraIssueListView.as_view(), name='issues-list'),
    path('issues/<str:issue_key>/', JiraIssueDetailView.as_view(), name='issue-detail'),
    path('dashboard/', JiraDashboardView.as_view(), name='dashboard'),
    path('dashboard/graph/', JiraGraphDashboardView.as_view(), name='graph-dashboard'),
]
