from django.urls import path
from .views import TaskStatusView, TaskListView, RestartCollectionView

urlpatterns = [
    path('', TaskListView.as_view(), name='task-list'),
    path('tasks/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
    path('restart-collection/<str:task_id>/', RestartCollectionView.as_view(), name='restart-collection'),
]
