from django.urls import path
from .views import FetchIssueTypesView, JiraIssueCollectView, IssueListView, IssueDetailView, IssueDeleteView

urlpatterns = [
    path('jira/issues/types/', FetchIssueTypesView.as_view(), name='fetch-issue-types'),
    path('/jira/issues/collect/', JiraIssueCollectView.as_view(), name='issue-collect'),
    path('/jira/issues/', IssueListView.as_view(), name='issue-list'),
    path('/jira/issues/<int:id>/', IssueDetailView.as_view(), name='issue-detail'),
    path('/jira/issues/<int:id>/delete/', IssueDeleteView.as_view(), name='issue-delete')
]
