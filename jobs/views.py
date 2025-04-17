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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

# Log configuration
logger = logging.getLogger(__name__)

# Class to serialize datetime objects to JSON
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TaskListView(generics.ListAPIView):
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    
    @extend_schema(
        summary="List all tasks",
        tags=['Jobs'],
        responses={
            200: OpenApiResponse(
                response=TaskSerializer(many=True),
                description="List of tasks with their current status"
            )
        },
        description='Get a list of all tasks with their current status'
    )
    def get(self, request, *args, **kwargs):
        # Get all tasks from the database
        tasks = self.get_queryset()
        
        # Update the status of all pending tasks
        for task in tasks:
            if task.status in ['PENDING', 'STARTED']:
                logger.info(f"Updating status of pending task: {task.task_id}")
                try:
                    # Get the task result from Celery
                    task_result = AsyncResult(task.task_id, app=current_app)
                    
                    # If the status has changed, update in the database
                    if task_result.state != task.status:
                        logger.info(f"Task status {task.task_id} changed from {task.status} to {task_result.state}")
                        task.status = task_result.state
                        
                        # If the task completed successfully, save the result
                        if task_result.state == 'SUCCESS':
                            # Convert the result to JSON using the custom encoder
                            result_json = json.dumps(task_result.result, cls=DateTimeEncoder)
                            task.result = json.loads(result_json)
                            logger.info(f"Task completed successfully: {task.task_id}")
                        # If the task failed, save the error
                        elif task_result.state == 'FAILURE':
                            task.error = str(task_result.result)
                            logger.error(f"Task failed: {task.task_id}, error: {task.error}")
                        
                        # Save changes to the database
                        task.save()
                        logger.info(f"Task status updated in database: {task.task_id}, new status: {task.status}")
                except Exception as e:
                    logger.error(f"Error updating task status {task.task_id}: {str(e)}", exc_info=True)
        
        # Serialize the tasks
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
        logger.info(f"Querying task status: {task_id}")
        
        try:
            # Try to get the task from the database
            task = Task.objects.get(task_id=task_id)
            logger.info(f"Task found in database: {task_id}, current status: {task.status}")
            
            # Get the task result from Celery
            task_result = AsyncResult(task_id, app=current_app)
            logger.info(f"Task state in Celery: {task_result.state}")
            
            # Update the task status in the database
            task.status = task_result.state
            
            # If the task completed successfully, save the result
            if task_result.state == 'SUCCESS':
                # Convert the result to JSON using the custom encoder
                result_json = json.dumps(task_result.result, cls=DateTimeEncoder)
                task.result = json.loads(result_json)
                logger.info(f"Task completed successfully: {task_id}")
            # If the task failed, save the error
            elif task_result.state == 'FAILURE':
                task.error = str(task_result.result)
                logger.error(f"Task failed: {task_id}, error: {task.error}")
            
            # Save changes to the database
            task.save()
            logger.info(f"Task status updated in database: {task_id}, new status: {task.status}")
            
            # Prepare the response
            response_data = {
                "task_id": task_id,
                "status": task_result.state,
                "error": str(task_result.result) if task_result.state == 'FAILURE' else None
            }
            
            # Add the result only if the task completed successfully
            if task_result.state == 'SUCCESS':
                response_data["result"] = task_result.result
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Task.DoesNotExist:
            logger.error(f"Task not found in database: {task_id}")
            return Response({
                "error": "Task not found in database",
                "task_id": task_id
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error checking task status: {task_id}, error: {str(e)}", exc_info=True)
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
        logger.info(f"Canceling task: {task_id}")
        
        try:
            # Try to get the task from the database
            task = Task.objects.get(task_id=task_id)
            logger.info(f"Task found in database: {task_id}, current status: {task.status}")
            
            # Get the task result from Celery
            task_result = AsyncResult(task_id, app=current_app)
            
            if task_result.state in ["PENDING", "STARTED"]:
                # Revoke the task in Celery
                task_result.revoke(terminate=True)
                logger.info(f"Task revoked in Celery: {task_id}")
                
                # Update the task status in the database
                task.status = "REVOKED"
                task.error = "Task canceled by user"
                task.save()
                logger.info(f"Task status updated in database: {task_id}, new status: {task.status}")
                
                return Response({
                    "task_id": task_id,
                    "status": "Task canceled and marked as failed"
                }, status=status.HTTP_200_OK)
            
            elif task_result.state == "SUCCESS":
                logger.info(f"Task already completed: {task_id}")
                return Response({
                    "error": "Task already completed"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            elif task_result.state == "REVOKED":
                logger.info(f"Task already canceled: {task_id}")
                return Response({
                    "error": "Task already canceled"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                logger.warning(f"Task not found or cannot be canceled: {task_id}")
                return Response({
                    "error": "Task not found or cannot be canceled"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Task.DoesNotExist:
            logger.error(f"Task not found in database: {task_id}")
            return Response({
                "error": "Task not found in database",
                "task_id": task_id
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error canceling task: {task_id}, error: {str(e)}", exc_info=True)
            return Response({
                "error": "Error canceling task",
                "task_id": task_id,
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
