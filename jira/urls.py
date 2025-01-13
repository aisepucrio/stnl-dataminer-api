from django.urls import path
from .views import IssueTypeCollectView, IssueCollectView, IssueListView, IssueDetailView, IssueDeleteView, IssueTypeListView, IssueTypeDetailView, IssueTypeDeleteView

urlpatterns = [
    path('issues/collect/', IssueCollectView.as_view(), name='collect-jira-issues'),
    path('issues/', IssueListView.as_view(), name='issues-list'),
    path('issues/<str:issue_key>/', IssueDetailView.as_view(), name='issue-detail'),
    path('issues/<str:issue_key>/delete/', IssueDeleteView.as_view(), name='issue-delete'),
    path('issuetypes/collect/', IssueTypeCollectView.as_view(), name='collect-issuetypes'),
    path('issuetypes/', IssueTypeListView.as_view(), name='issuetype-list'),
    path('issuetypes/<int:issuetype_id>/', IssueTypeDetailView.as_view(), name='issuetype-detail'),
    path('issuetypes/<int:issuetype_id>/delete/', IssueTypeDeleteView.as_view(), name='issuetype-delete')
]
