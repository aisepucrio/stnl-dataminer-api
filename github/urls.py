from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'commits/collect', views.GitHubCommitViewSet, basename='commit-collect')
router.register(r'commits/collect-by-sha', views.GitHubCommitByShaViewSet, basename='commit-collect-by-sha')
router.register(r'issues/collect', views.GitHubIssueViewSet, basename='issue-collect')
router.register(r'pull-requests/collect', views.GitHubPullRequestViewSet, basename='pullrequest-collect')
router.register(r'branches/collect', views.GitHubBranchViewSet, basename='branch-collect')
router.register(r'metadata/collect', views.GitHubMetadataViewSet, basename='metadata-collect')

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
    path('metadata/', views.MetadataListView.as_view(), name='metadata-list'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]
