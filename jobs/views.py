from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Task

# View to handle GET and DELETE requests for a task
class TaskDetailView(APIView):

    def get(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id)
            return Response({
                "id": task.id,
                "status": task.status,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "metadata": task.metadata
            }, status=status.HTTP_200_OK)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id)
            task.cancel()
            return Response({"status": "Task canceled and marked as failed"}, status=status.HTTP_204_NO_CONTENT)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
