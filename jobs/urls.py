from django.urls import path
from .views import TaskStatusView, TaskListView

urlpatterns = [
    path('', TaskListView.as_view(), name='task-list'),
    path('tasks/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
]
