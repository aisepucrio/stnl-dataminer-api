import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from ..models import GitHubCommit, GitHubBranch, GitHubMetadata, GitHubIssuePullRequest, GitHubAuthor
from ..serializers import (
    GitHubCommitSerializer,
    GitHubBranchSerializer,
    GitHubMetadataSerializer,
    GitHubIssuePullRequestSerializer,
    GitHubAuthorSerializer
)
from utils.lookup import get_filterset_fields as _get_filterset_fields, get_search_fields as _get_search_fields

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


@extend_schema(tags=["GitHub"], summary="List all GitHub commits")
class CommitListView(generics.ListAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubCommit)
    search_fields = _get_search_fields(GitHubCommit)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination


@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub commit")
class CommitDetailView(generics.RetrieveAPIView):
    queryset = GitHubCommit.objects.all()
    serializer_class = GitHubCommitSerializer
    lookup_field = 'sha'


@extend_schema(tags=["GitHub"], summary="List all GitHub issues")
class IssueListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubIssuePullRequest)
    search_fields = _get_search_fields(GitHubIssuePullRequest)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination


@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub issue")
class IssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='issue')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'


@extend_schema(tags=["GitHub"], summary="List all GitHub pull requests")
class PullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubIssuePullRequest)
    search_fields = _get_search_fields(GitHubIssuePullRequest)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination


@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub pull request")
class PullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.filter(data_type='pull_request')
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'


@extend_schema(tags=["GitHub"], summary="List all GitHub branches")
class BranchListView(generics.ListAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubBranch)
    search_fields = _get_search_fields(GitHubBranch)
    pagination_class = StandardResultsSetPagination
    ordering_fields = '__all__'


@extend_schema(tags=["GitHub"], summary="Retrieve a specific GitHub branch")
class BranchDetailView(generics.RetrieveAPIView):
    queryset = GitHubBranch.objects.all()
    serializer_class = GitHubBranchSerializer
    lookup_field = 'name'


@extend_schema(tags=["GitHub"], summary="List all GitHub repository metadata")
class MetadataListView(generics.ListAPIView):
    queryset = GitHubMetadata.objects.all()
    serializer_class = GitHubMetadataSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubMetadata)
    search_fields = _get_search_fields(GitHubMetadata)
    ordering_fields = '__all__'
    pagination_class = StandardResultsSetPagination


class IssuePullRequestListView(generics.ListAPIView):
    queryset = GitHubIssuePullRequest.objects.all()
    serializer_class = GitHubIssuePullRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubIssuePullRequest)
    search_fields = _get_search_fields(GitHubIssuePullRequest)
    ordering_fields = _get_filterset_fields(GitHubIssuePullRequest)
    pagination_class = StandardResultsSetPagination


class IssuePullRequestDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssuePullRequest.objects.all()
    serializer_class = GitHubIssuePullRequestSerializer
    lookup_field = 'record_id'


class UserListView(generics.ListAPIView):
    queryset = GitHubAuthor.objects.all()
    serializer_class = GitHubAuthorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(GitHubAuthor)
    search_fields = _get_search_fields(GitHubAuthor)
    ordering_fields = "__all__"
    pagination_class = StandardResultsSetPagination 