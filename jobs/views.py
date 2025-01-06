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

        try:
            # Tenta acessar o estado da task
            # Se a task não existir, isso geralmente retorna 'PENDING'
            state = task_result.state
            
            # Se o estado for PENDING, vamos tentar obter mais informações
            if state == 'PENDING':
                # Tenta acessar o resultado para verificar se a task realmente existe
                task_result.get(timeout=1)
            
            print(f'[Task Status Check] Current Celery App Name: {current_app.main}')
            print(f'[Task Status Check] Broker URL: {current_app.conf.broker_url}')
            print(f'[Task Status Check] Registered Tasks: {list(current_app.tasks.keys())}')
        
            return Response({
                "task_id": task_id,
                "status": state
            }, status=status.HTTP_200_OK)
            
        except TimeoutError:
            # Se der timeout, provavelmente a task ainda está realmente pendente
            return Response({
                "task_id": task_id,
                "status": "PENDING"
            }, status=status.HTTP_200_OK)
            
        except Exception:
            # Se ocorrer qualquer outro erro, provavelmente a task não existe
            return Response({
                "error": "Task not found",
                "task_id": task_id
            }, status=status.HTTP_404_NOT_FOUND)

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
