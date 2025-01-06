from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from celery import current_app

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from celery import current_app

class TaskStatusView(APIView):
    def get(self, request, task_id):
        task_result = AsyncResult(task_id, app=current_app)

        print(f'[Task Status Check] Current Celery App Name: {current_app.main}')
        print(f'[Task Status Check] Broker URL: {current_app.conf.broker_url}')
        print(f'[Task Status Check] Registered Tasks: {list(current_app.tasks.keys())}')
    
        return Response({
            "task_id": task_id,
            "status": task_result.state
        }, status=status.HTTP_200_OK)

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
