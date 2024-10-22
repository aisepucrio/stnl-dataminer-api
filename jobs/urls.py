from django.urls import path
from .views import TaskDetailView

urlpatterns = [
    path('task/<int:task_id>/', TaskDetailView.as_view(), name='task-detail'),
]
