from django.urls import path
from .views import JiraIssueCollectView, IssueListView, IssueDetailView

urlpatterns = [
    path('issues/collect/', JiraIssueCollectView.as_view(), name='issue-collect'),
    path('issues/', IssueListView.as_view(), name='issue-list'),
    path('issues/<int:id>/', IssueDetailView.as_view(), name='issue-detail'),
]
