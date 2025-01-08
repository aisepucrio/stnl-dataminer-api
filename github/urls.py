from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'commits/mine', views.GitHubCommitViewSet, basename='commit-mine')
router.register(r'issues/mine', views.GitHubIssueViewSet, basename='github-issue-mine')
router.register(r'pull-requests/mine', views.GitHubPullRequestViewSet, basename='pullrequest-mine')
router.register(r'branches/mine', views.GitHubBranchViewSet, basename='branch-mine')

urlpatterns = [
    path('', include(router.urls)),
    
    path('commits/', views.CommitListView.as_view(), name='commit-list'),
    path('commits/<str:sha>/', views.CommitDetailView.as_view(), name='commit-detail'),
    path('issues/', views.IssueListView.as_view(), name='issue-list'),
    path('issues/<int:issue_id>/', views.IssueDetailView.as_view(), name='issue-detail'),
    path('pull-requests/', views.PullRequestListView.as_view(), name='pullrequest-list'),
    path('pull-requests/<int:pr_id>/', views.PullRequestDetailView.as_view(), name='pullrequest-detail'),
    path('branches/', views.BranchListView.as_view(), name='branch-list'),
    path('branches/<str:name>/', views.BranchDetailView.as_view(), name='branch-detail'),
]
