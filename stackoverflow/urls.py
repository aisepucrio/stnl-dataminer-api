# Em stackoverflow/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Importa os módulos 'collect' e 'lookup' da nossa nova pasta 'views'
from .views import collect, lookup 

router = DefaultRouter()

# Rota para as tarefas de COLETA (ex: /api/stackoverflow/collect/collect-questions/)
router.register(r'collect', collect.StackOverflowViewSet, basename='stackoverflow-collect')

# Rota NOVA para a CONSULTA de perguntas (ex: /api/stackoverflow/questions/)
router.register(r'questions', lookup.QuestionViewSet, basename='stackoverflow-question')

urlpatterns = [
    path('', include(router.urls)),
]