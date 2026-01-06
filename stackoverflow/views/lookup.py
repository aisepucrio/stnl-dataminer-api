from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from ..models import StackQuestion
from ..serializers import StackQuestionSerializer


class StandardPagination(PageNumberPagination):
    """Defines a standard pagination scheme for API responses."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows questions to be viewed
    with support for filtering, text search, and ordering.
    """
    queryset = StackQuestion.objects.all()
    serializer_class = StackQuestionSerializer

    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Fields for exact match filtering (e.g., ?is_answered=true)
    filterset_fields = ['is_answered', 'owner__user_id', 'tags__name']

    # Fields for text search (e.g., ?search=api)
    search_fields = ['title', 'body']

    # Fields for sorting results (e.g., ?ordering=-score)
    ordering_fields = ['score', 'view_count', 'answer_count', 'creation_date']
