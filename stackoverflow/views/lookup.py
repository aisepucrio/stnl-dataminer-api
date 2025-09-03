from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from ..models import StackQuestion
from ..serializers import StackQuestionSerializer

class StandardPagination(PageNumberPagination):
    """Define um padrão de paginação para as respostas."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite que as perguntas sejam visualizadas,
    com suporte a filtros, busca e ordenação.
    """
    queryset = StackQuestion.objects.all()
    serializer_class = StackQuestionSerializer
    
    # --- A MÁGICA ACONTECE AQUI ---
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Campos para filtrar por valor exato (ex: ?is_answered=true)
    filterset_fields = ['is_answered', 'owner__user_id', 'tags__name']
    
    # Campos para busca por texto (ex: ?search=api)
    search_fields = ['title', 'body']
    
    # Campos para ordenação (ex: ?ordering=-score)
    ordering_fields = ['score', 'view_count', 'answer_count', 'creation_date']