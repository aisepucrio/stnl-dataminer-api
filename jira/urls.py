from django.urls import path
from .views import IssueCollectView, IssueListView, IssueDetailView, IssueDeleteView

urlpatterns = [
    path('issues/collect/', IssueCollectView.as_view(), name='collect-jira-issues'),
    path('issues/', IssueListView.as_view(), name='issues-list'),
    path('issues/<str:issue_key>/', IssueDetailView.as_view(), name='issue-detail'),
    path('issues/<str:issue_key>/delete/', IssueDeleteView.as_view(), name='issue-delete')
]
