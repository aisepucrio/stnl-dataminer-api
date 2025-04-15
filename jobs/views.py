from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
from celery import current_app
from rest_framework import generics
from .models import Task
from .serializers import TaskSerializer
import logging
import json
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter

# Configuração de logs
logger = logging.getLogger(__name__)

# Classe para serializar objetos datetime para JSON
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TaskListView(generics.ListAPIView):
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    
    def get(self, request, *args, **kwargs):
        # Obtém todas as tasks do banco
        tasks = self.get_queryset()
        
        # Atualiza o status de todas as tasks pendentes
        for task in tasks:
            if task.status in ['PENDING', 'STARTED']:
                logger.info(f"Atualizando status da task pendente: {task.task_id}")
                try:
                    # Obtém o resultado da task do Celery
                    task_result = AsyncResult(task.task_id, app=current_app)
                    
                    # Se o status mudou, atualiza no banco
                    if task_result.state != task.status:
                        logger.info(f"Status da task {task.task_id} mudou de {task.status} para {task_result.state}")
                        task.status = task_result.state
                        
                        # Se a task foi concluída com sucesso, salva o resultado
                        if task_result.state == 'SUCCESS':
                            # Converte o resultado para JSON usando o encoder personalizado
                            result_json = json.dumps(task_result.result, cls=DateTimeEncoder)
                            task.result = json.loads(result_json)
                            logger.info(f"Task concluída com sucesso: {task.task_id}")
                        # Se a task falhou, salva o erro
                        elif task_result.state == 'FAILURE':
                            task.error = str(task_result.result)
                            logger.error(f"Task falhou: {task.task_id}, erro: {task.error}")
                        
                        # Salva as alterações no banco
                        task.save()
                        logger.info(f"Status da task atualizado no banco: {task.task_id}, novo status: {task.status}")
                except Exception as e:
                    logger.error(f"Erro ao atualizar status da task {task.task_id}: {str(e)}", exc_info=True)
        
        # Serializa as tasks
        serializer = self.get_serializer(tasks, many=True)
        
        return Response({
            "count": tasks.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)

class TaskStatusView(APIView):
    @extend_schema(
        summary="Get task status",
        tags=['Jobs'],
        parameters=[
            OpenApiParameter(name='task_id', type=str, location=OpenApiParameter.PATH, description='Celery task ID'),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"}
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "task_id": {"type": "string"}
                }
            }
        },
        description='Get the status of a Celery task'
    )
    def get(self, request, task_id):
        logger.info(f"Consultando status da task: {task_id}")
        
        try:
            # Tenta obter a task do banco de dados
            task = Task.objects.get(task_id=task_id)
            logger.info(f"Task encontrada no banco: {task_id}, status atual: {task.status}")
            
            # Obtém o resultado da task do Celery
            task_result = AsyncResult(task_id, app=current_app)
            logger.info(f"Estado da task no Celery: {task_result.state}")
            
            # Atualiza o status da task no banco de dados
            task.status = task_result.state
            
            # Se a task foi concluída com sucesso, salva o resultado
            if task_result.state == 'SUCCESS':
                # Converte o resultado para JSON usando o encoder personalizado
                result_json = json.dumps(task_result.result, cls=DateTimeEncoder)
                task.result = json.loads(result_json)
                logger.info(f"Task concluída com sucesso: {task_id}")
            # Se a task falhou, salva o erro
            elif task_result.state == 'FAILURE':
                task.error = str(task_result.result)
                logger.error(f"Task falhou: {task_id}, erro: {task.error}")
            
            # Salva as alterações no banco
            task.save()
            logger.info(f"Status da task atualizado no banco: {task_id}, novo status: {task.status}")
            
            # Prepara a resposta
            response_data = {
                "task_id": task_id,
                "status": task_result.state,
                "error": str(task_result.result) if task_result.state == 'FAILURE' else None
            }
            
            # Adiciona o resultado apenas se a task foi concluída com sucesso
            if task_result.state == 'SUCCESS':
                response_data["result"] = task_result.result
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Task.DoesNotExist:
            logger.error(f"Task não encontrada no banco: {task_id}")
            return Response({
                "error": "Task not found in database",
                "task_id": task_id
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Erro ao consultar status da task: {task_id}, erro: {str(e)}", exc_info=True)
            return Response({
                "error": "Error checking task status",
                "task_id": task_id,
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Cancel running task",
        tags=['Jobs'],
        parameters=[
            OpenApiParameter(name='task_id', type=str, location=OpenApiParameter.PATH, description='Celery task ID'),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        description='Cancel a running Celery task'
    )
    def delete(self, request, task_id):
        logger.info(f"Cancelando task: {task_id}")
        
        try:
            # Tenta obter a task do banco de dados
            task = Task.objects.get(task_id=task_id)
            logger.info(f"Task encontrada no banco: {task_id}, status atual: {task.status}")
            
            # Obtém o resultado da task do Celery
            task_result = AsyncResult(task_id, app=current_app)
            
            if task_result.state in ["PENDING", "STARTED"]:
                # Revoga a task no Celery
                task_result.revoke(terminate=True)
                logger.info(f"Task revogada no Celery: {task_id}")
                
                # Atualiza o status da task no banco de dados
                task.status = "REVOKED"
                task.error = "Task canceled by user"
                task.save()
                logger.info(f"Status da task atualizado no banco: {task_id}, novo status: {task.status}")
                
                return Response({
                    "task_id": task_id,
                    "status": "Task canceled and marked as failed"
                }, status=status.HTTP_200_OK)
            
            elif task_result.state == "SUCCESS":
                logger.info(f"Task já concluída: {task_id}")
                return Response({
                    "error": "Task already completed"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            elif task_result.state == "REVOKED":
                logger.info(f"Task já cancelada: {task_id}")
                return Response({
                    "error": "Task already canceled"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                logger.warning(f"Task não encontrada ou não pode ser cancelada: {task_id}")
                return Response({
                    "error": "Task not found or cannot be canceled"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Task.DoesNotExist:
            logger.error(f"Task não encontrada no banco: {task_id}")
            return Response({
                "error": "Task not found in database",
                "task_id": task_id
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Erro ao cancelar task: {task_id}, erro: {str(e)}", exc_info=True)
            return Response({
                "error": "Error canceling task",
                "task_id": task_id,
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
