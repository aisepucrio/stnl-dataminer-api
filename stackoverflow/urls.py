from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import collect, lookup
from .views.dashboard import DashboardView, GraphDashboardView, TagDateRangeView
from stackoverflow.export import ExportStackoverflowCSVView

router = DefaultRouter()

# Route for collecting questions (ex: POST /api/stackoverflow/collect/)
router.register(r'collect', collect.StackOverflowViewSet, basename='stackoverflow-collect')
router.register(r'questions', lookup.QuestionViewSet, basename='stackoverflow-question')

urlpatterns = [
    path('', include(router.urls)),
    path("export/", ExportStackoverflowCSVView.as_view(), name="stackoverflow_export_csv"),
    path("dashboard/", DashboardView.as_view(), name="stackoverflow-dashboard"),
    path("dashboard/graph/", GraphDashboardView.as_view(), name="stackoverflow-graph-dashboard"),
    path("date-range/", TagDateRangeView.as_view(), name="stackoverflow-date-range"),
]
