from django.db import models
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from jira.models import JiraIssue, JiraProject, JiraSprint, JiraComment, JiraCommit, JiraUser, JiraChecklist, JiraIssueType, JiraIssueLink, JiraActivityLog, JiraHistory, JiraHistoryItem
from jira.serializers import JiraIssueSerializer, JiraProjectSerializer, JiraUserSerializer, JiraSprintSerializer, JiraCommentSerializer, JiraChecklistSerializer, JiraIssueTypeSerializer, JiraIssueLinkSerializer, JiraCommitSerializer, JiraActivityLogSerializer, JiraHistorySerializer, JiraHistoryItemSerializer

from utils.lookup import get_filterset_fields as _get_filterset_fields, get_search_fields as _get_search_fields

class StandardPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

@extend_schema(
    tags=['Jira']
)
class JiraProjectListView(generics.ListAPIView):
    queryset = JiraProject.objects.all().order_by('id')
    serializer_class = JiraProjectSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(JiraProject)
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraProject)


@extend_schema(
    tags=['Jira']
)
class JiraUserListView(generics.ListAPIView):
    queryset = JiraUser.objects.all().order_by('accountId')
    serializer_class = JiraUserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = _get_filterset_fields(JiraUser)
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraUser)


@extend_schema(
    tags=['Jira']
)
class JiraIssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all().order_by('issue_id')
    serializer_class = JiraIssueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraIssue),
        'project': ['exact'],
        'project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraIssue)


@extend_schema(
    tags=['Jira']
)
class JiraChecklistListView(generics.ListAPIView):
    queryset = JiraChecklist.objects.all().order_by('id')
    serializer_class = JiraChecklistSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraChecklist),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraChecklist)


@extend_schema(
    tags=['Jira']
)
class JiraIssueTypeListView(generics.ListAPIView):
    queryset = JiraIssueType.objects.all().order_by('id')
    serializer_class = JiraIssueTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraIssueType),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraIssueType)


@extend_schema(
    tags=['Jira']
)
class JiraSprintListView(generics.ListAPIView):
    queryset = JiraSprint.objects.all().order_by('id')
    serializer_class = JiraSprintSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraSprint),
        'issues__project': ['exact'],
        'issues__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraSprint)


@extend_schema(
    tags=['Jira']
)
class JiraCommentListView(generics.ListAPIView):
    queryset = JiraComment.objects.all().order_by('id')
    serializer_class = JiraCommentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraComment),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraComment)


@extend_schema(
    tags=['Jira']
)
class JiraIssueLinkListView(generics.ListAPIView):
    queryset = JiraIssueLink.objects.all().order_by('id')
    serializer_class = JiraIssueLinkSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraIssueLink),
        'issue__project': ['exact'],
        'issue__project__id': ['exact'],
        'linked_issue__project': ['exact'],
        'linked_issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraIssueLink)


@extend_schema(
    tags=['Jira']
)
class JiraCommitListView(generics.ListAPIView):
    queryset = JiraCommit.objects.all().order_by('id')
    serializer_class = JiraCommitSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraCommit),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraCommit)


@extend_schema(
    tags=['Jira']
)
class JiraActivityLogListView(generics.ListAPIView):
    queryset = JiraActivityLog.objects.all().order_by('id')
    serializer_class = JiraActivityLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraActivityLog),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraActivityLog)


@extend_schema(
    tags=['Jira']
)
class JiraHistoryListView(generics.ListAPIView):
    queryset = JiraHistory.objects.all().order_by('id')
    serializer_class = JiraHistorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraHistory),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraHistory)


@extend_schema(
    tags=['Jira']
)
class JiraHistoryItemListView(generics.ListAPIView):
    queryset = JiraHistoryItem.objects.all().order_by('id')
    serializer_class = JiraHistoryItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraHistoryItem),
        'history__issue__project': ['exact'],
        'history__issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination
    search_fields = _get_search_fields(JiraHistoryItem)