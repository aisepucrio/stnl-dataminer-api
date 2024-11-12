from django.urls import path
from .views import TaskStatusView, TaskCancelView

urlpatterns = [
    path('<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
    path('<str:task_id>/cancel/', TaskCancelView.as_view(), name='task-cancel'),
]
