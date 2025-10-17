# Em stackoverflow/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import collect, lookup
from stackoverflow.export import ExportStackoverflowCSVView

router = DefaultRouter()
router.register(r'collect', collect.StackOverflowViewSet, basename='stackoverflow-collect')
router.register(r'questions', lookup.QuestionViewSet, basename='stackoverflow-question')

urlpatterns = [
    path('', include(router.urls)),
    path("export/", ExportStackoverflowCSVView.as_view(), name="stackoverflow_export_csv"),
]
