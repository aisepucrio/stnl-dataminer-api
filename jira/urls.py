from django.urls import path
from .views import FetchIssueTypesView, JiraIssueCollectView, IssueListView, IssueDetailView, IssueDeleteView

urlpatterns = [
    path('issues/types/', FetchIssueTypesView.as_view(), name='fetch-issuetypes'),
    path('issues/collect/', JiraIssueCollectView.as_view(), name='issue-collect'),
    path('issues/', IssueListView.as_view(), name='issue-list'),
    path('issues/<int:issue_id>/', IssueDetailView.as_view(), name='issue-detail'),
    path('issues/<int:issue_id>/delete/', IssueDeleteView.as_view(), name='issue-delete')
]
