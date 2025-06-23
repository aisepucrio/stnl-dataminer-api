from django.db import models
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema

from jira.models import JiraIssue, JiraProject, JiraSprint, JiraComment, JiraCommit, JiraUser, JiraChecklist, JiraIssueType, JiraIssueLink, JiraActivityLog, JiraHistory, JiraHistoryItem
from jira.serializers import JiraIssueSerializer, JiraProjectSerializer, JiraUserSerializer, JiraSprintSerializer, JiraCommentSerializer, JiraChecklistSerializer, JiraIssueTypeSerializer, JiraIssueLinkSerializer, JiraCommitSerializer, JiraActivityLogSerializer, JiraHistorySerializer, JiraHistoryItemSerializer

def _get_filterset_fields(model):
    """Generate filterset_fields dictionary for django-filters"""
    filterset_fields = {}
    for field in model._meta.fields:
        if isinstance(field, models.JSONField):
            continue
        elif isinstance(field, (models.DateField, models.TimeField, models.DateTimeField)):
            filterset_fields[field.name] = ['exact', 'gte', 'lte', 'year', 'month', 'day']
        elif isinstance(field, (models.CharField, models.TextField)):
            filterset_fields[field.name] = ['exact', 'icontains', 'iexact']
        elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField)):
            filterset_fields[field.name] = ['exact', 'gte', 'lte']
        else:
            filterset_fields[field.name] = ['exact']
    
    return filterset_fields

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
    filterset_fields = _get_filterset_fields(JiraProject)
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraUserListView(generics.ListAPIView):
    queryset = JiraUser.objects.all()
    serializer_class = JiraUserSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = _get_filterset_fields(JiraUser)
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraIssueListView(generics.ListAPIView):
    queryset = JiraIssue.objects.all()
    serializer_class = JiraIssueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraIssue),
        'project': ['exact'],
        'project__id': ['exact']
    }
    ordering_fields = '__all__'
    search_fields = ['summary', 'description']
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraChecklistListView(generics.ListAPIView):
    queryset = JiraChecklist.objects.all()
    serializer_class = JiraChecklistSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraChecklist),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraIssueTypeListView(generics.ListAPIView):
    queryset = JiraIssueType.objects.all()
    serializer_class = JiraIssueTypeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraIssueType),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraSprintListView(generics.ListAPIView):
    queryset = JiraSprint.objects.all()
    serializer_class = JiraSprintSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraSprint),
        'issues__project': ['exact'],
        'issues__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraCommentListView(generics.ListAPIView):
    queryset = JiraComment.objects.all()
    serializer_class = JiraCommentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraComment),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraIssueLinkListView(generics.ListAPIView):
    queryset = JiraIssueLink.objects.all()
    serializer_class = JiraIssueLinkSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraIssueLink),
        'issue__project': ['exact'],
        'issue__project__id': ['exact'],
        'linked_issue__project': ['exact'],
        'linked_issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraCommitListView(generics.ListAPIView):
    queryset = JiraCommit.objects.all()
    serializer_class = JiraCommitSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraCommit),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraActivityLogListView(generics.ListAPIView):
    queryset = JiraActivityLog.objects.all()
    serializer_class = JiraActivityLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraActivityLog),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraHistoryListView(generics.ListAPIView):
    queryset = JiraHistory.objects.all()
    serializer_class = JiraHistorySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraHistory),
        'issue__project': ['exact'],
        'issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination


@extend_schema(
    tags=['Jira']
)
class JiraHistoryItemListView(generics.ListAPIView):
    queryset = JiraHistoryItem.objects.all()
    serializer_class = JiraHistoryItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        **_get_filterset_fields(JiraHistoryItem),
        'history__issue__project': ['exact'],
        'history__issue__project__id': ['exact']
    }
    ordering_fields = '__all__'
    pagination_class = StandardPagination