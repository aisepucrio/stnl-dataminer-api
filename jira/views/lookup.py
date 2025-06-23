from django.db import models
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from jira.models import JiraIssue, JiraProject, JiraSprint, JiraComment, JiraCommit, JiraUser, JiraChecklist, JiraIssueType, JiraIssueLink, JiraActivityLog, JiraHistory, JiraHistoryItem
from jira.serializers import JiraIssueSerializer, JiraProjectSerializer, JiraUserSerializer, JiraSprintSerializer, JiraCommentSerializer, JiraChecklistSerializer, JiraIssueTypeSerializer, JiraIssueLinkSerializer, JiraCommitSerializer, JiraActivityLogSerializer, JiraHistorySerializer, JiraHistoryItemSerializer

def _get_filter_fields_and_date_filters(model):
    filter_fields = [f for f in model._meta.fields if not isinstance(f, models.JSONField)]
    filterset_fields = {}
    for f in filter_fields:
        if isinstance(f, (models.DateField, models.TimeField, models.DateTimeField)):
            filterset_fields[f.name] = ['exact', 'gte', 'lte']
        if isinstance(f, (models.CharField, models.TextField)):
            filterset_fields[f.name] = ['exact', 'icontains']
        else:
            filterset_fields[f.name] = ['exact']
    
    return filter_fields, filterset_fields

class StandardPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

@extend_schema(
    tags=['Jira']
)
class JiraProjectListView(generics.ListAPIView):
    queryset = JiraProject.objects.all()
    serializer_class = JiraProjectSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraProject)
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraUserListView(generics.ListAPIView):
    queryset = JiraUser.objects.all()
    serializer_class = JiraUserSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraUser)
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraIssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraIssue)
    filterset_fields.update({
        'project': ['exact'],
        'project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    search_fields = ['summary', 'description']
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraChecklistListView(generics.ListAPIView):
    queryset = JiraChecklist.objects.all()
    serializer_class = JiraChecklistSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraChecklist)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraIssueTypeListView(generics.ListAPIView):
    queryset = JiraIssueType.objects.all()
    serializer_class = JiraIssueTypeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraIssueType)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraSprintListView(generics.ListAPIView):
    queryset = JiraSprint.objects.all()
    serializer_class = JiraSprintSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraSprint)
    filterset_fields.update({
        'issues__project': ['exact'],
        'issues__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraCommentListView(generics.ListAPIView):
    queryset = JiraComment.objects.all()
    serializer_class = JiraCommentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraComment)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraIssueLinkListView(generics.ListAPIView):
    queryset = JiraIssueLink.objects.all()
    serializer_class = JiraIssueLinkSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraIssueLink)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact'],
        'linked_issue__project': ['exact'],
        'linked_issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraCommitListView(generics.ListAPIView):
    queryset = JiraCommit.objects.all()
    serializer_class = JiraCommitSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraCommit)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraActivityLogListView(generics.ListAPIView):
    queryset = JiraActivityLog.objects.all()
    serializer_class = JiraActivityLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraActivityLog)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraHistoryListView(generics.ListAPIView):
    queryset = JiraHistory.objects.all()
    serializer_class = JiraHistorySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraHistory)
    filterset_fields.update({
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraHistoryItemListView(generics.ListAPIView):
    queryset = JiraHistoryItem.objects.all()
    serializer_class = JiraHistoryItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_fields, filterset_fields = _get_filter_fields_and_date_filters(JiraHistoryItem)
    filterset_fields.update({
        'history__issue__project': ['exact'],
        'history__issue__project__id': ['exact']
    })
    ordering_fields = [f.name for f in filter_fields]
    pagination_class = StandardPagination