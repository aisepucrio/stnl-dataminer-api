# Em stackoverflow/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import collect, lookup

router = DefaultRouter()

# Rota para as tarefas de COLETA (ex: POST /api/stackoverflow/collect/)
router.register(r'collect', collect.StackOverflowViewSet, basename='stackoverflow-collect')

# Rota para a CONSULTA de perguntas (ex: GET /api/stackoverflow/questions/)
router.register(r'questions', lookup.QuestionViewSet, basename='stackoverflow-question')

urlpatterns = [
    path('', include(router.urls)),
]