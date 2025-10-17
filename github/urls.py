from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views.lookup import (
    CommitListView, CommitDetailView,
    IssueListView, IssueDetailView,
    PullRequestListView, PullRequestDetailView,
    BranchListView, BranchDetailView,
    MetadataListView,
    IssuePullRequestListView, IssuePullRequestDetailView,
    UserListView,
)
from .views.dashboard import DashboardView, GraphDashboardView, RepositoryDateRangeView
from .views.export import ExportDataView

app_name = 'github'

router = DefaultRouter()
router.register(r'commits/collect', views.GitHubCommitViewSet, basename='commit-collect')
router.register(r'commits/collect-by-sha', views.GitHubCommitByShaViewSet, basename='commit-collect-by-sha')
router.register(r'issues/collect', views.GitHubIssueViewSet, basename='issue-collect')
router.register(r'pull-requests/collect', views.GitHubPullRequestViewSet, basename='pullrequest-collect')
router.register(r'branches/collect', views.GitHubBranchViewSet, basename='branch-collect')
router.register(r'metadata/collect', views.GitHubMetadataViewSet, basename='metadata-collect')
router.register(r'collect-all', views.GitHubCollectAllViewSet, basename='collect-all')

urlpatterns = [
    # PRIORIZE a rota de export antes do router
    path('export/', ExportDataView.as_view(), name='export-data'),

    path('', include(router.urls)),

    path('commits/', CommitListView.as_view(), name='commit-list'),
    path('commits/<str:sha>/', CommitDetailView.as_view(), name='commit-detail'),
    path('issues/', IssueListView.as_view(), name='issue-list'),
    path('issues/<int:issue_id>/', IssueDetailView.as_view(), name='issue-detail'),
    path('pull-requests/', PullRequestListView.as_view(), name='pullrequest-list'),
    path('pull-requests/<int:pr_id>/', PullRequestDetailView.as_view(), name='pullrequest-detail'),
    path('branches/', BranchListView.as_view(), name='branch-list'),
    path('branches/<str:name>/', BranchDetailView.as_view(), name='branch-detail'),
    path('metadata/', MetadataListView.as_view(), name='metadata-list'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/graph/', GraphDashboardView.as_view(), name='graph-dashboard'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('date-range/', RepositoryDateRangeView.as_view(), name='github-date-range'),
]
