from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GitHubCommitViewSet, GitHubIssueViewSet, GitHubPullRequestViewSet, GitHubBranchViewSet, task_status

router = DefaultRouter()
router.register(r'commits', GitHubCommitViewSet, basename='commit')
router.register(r'issues', GitHubIssueViewSet, basename='github-issue')
router.register(r'pull-requests', GitHubPullRequestViewSet, basename='pullrequest')
router.register(r'branches', GitHubBranchViewSet, basename='branch')

urlpatterns = [
    path('github/', include(router.urls)),
    path('tasks/<str:task_id>/status/', task_status, name='task_status'), 
]
