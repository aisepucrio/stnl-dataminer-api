# jobs/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from celery import current_app

class TaskStatusView(APIView):
    def get(self, request, task_id):
        task_result = AsyncResult(task_id, app=current_app)
        
        if task_result.state in ["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED"]:
            return Response({
                "task_id": task_id,
                "status": task_result.state,
                "message": "Task completed successfully" if task_result.state == "SUCCESS" else None,
                "error": str(task_result.result) if task_result.state in ["FAILURE", "REVOKED"] else None
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)


class TaskCancelView(APIView):
    def delete(self, request, task_id):
        task_result = AsyncResult(task_id, app=current_app)

        if task_result.state in ["PENDING", "STARTED"]:
            # Cancela a task - em Celery, marcamos como revoked
            task_result.revoke(terminate=True)
            return Response({
                "task_id": task_id,
                "status": "Task canceled and marked as failed"
            }, status=status.HTTP_200_OK)
        
        elif task_result.state == "SUCCESS":
            return Response({
                "error": "Task already completed"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        elif task_result.state == "REVOKED":
            return Response({
                "error": "Task already canceled"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            return Response({
                "error": "Task not found or cannot be canceled"
            }, status=status.HTTP_404_NOT_FOUND)
