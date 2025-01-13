from django.urls import path
from .views import IssueCollectView, IssueListView, IssueDetailView

urlpatterns = [
    path('issues/collect/', IssueCollectView.as_view(), name='collect-jira-issues'),
    path('issues/', IssueListView.as_view(), name='issues-list'),
    path('issues/<str:issue_key>/', IssueDetailView.as_view(), name='issue-detail')
]
