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
from datetime import datetime, timedelta
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
                    "status": "Task canceled"
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


class RestartCollectionView(APIView):
    """
    Generic view to restart collection tasks.
    Routes to GitHub or Jira restart handlers based on task type.
    """
    
    @extend_schema(
        summary="Restart collection from last progress + 1 day",
        tags=["Jobs"],
        parameters=[
            OpenApiParameter(
                name='task_id',
                type=str,
                location=OpenApiParameter.PATH,
                description='Task ID to restart'
            )
        ],
        responses={
            202: OpenApiResponse(description="Restart scheduled successfully"),
            404: OpenApiResponse(description="Task not found"),
            409: OpenApiResponse(description="Task already finished - restart denied")
        }
    )
    def post(self, request, task_id):
        logger.info(f"RestartCollectionView: attempting restart for task_id={task_id}")
        
        try:
            task_obj = Task.objects.get(task_id=task_id)
            logger.info(f"Found task: type={task_obj.type}, status={task_obj.status}")
        except Task.DoesNotExist:
            logger.error(f"Task not found: {task_id}")
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if task can be restarted
        current_status = (getattr(task_obj, "status", "") or "").upper()
        if current_status == "SUCCESS":
            return Response(
                {"error": "Task already finished. Restart denied."},
                status=status.HTTP_409_CONFLICT
            )

        # Calculate resume_from = date_last_update + 1 day; fallback to date_init
        resume_from = getattr(task_obj, "date_last_update", None)
        if resume_from:
            resume_from = (resume_from + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            resume_from = getattr(task_obj, "date_init", None)

        # Route to appropriate restart handler based on task type
        task_type = getattr(task_obj, "type", "")
        logger.info(f"Task type: '{task_type}'")
        
        if task_type.startswith('github_'):
            # GitHub task 
            logger.info("Routing to GitHub restart handler")
            try:
                from github.tasks import restart_collection
                async_result = restart_collection.apply_async(kwargs={
                    "task_pk": task_obj.id
                })
                logger.info(f"GitHub restart task dispatched: {async_result.id}")
            except Exception as e:
                logger.error(f"Error dispatching GitHub restart: {str(e)}")
                return Response({
                    "error": f"Error dispatching restart: {str(e)}",
                    "task_id": task_id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif task_type.startswith('jira_'):
            # Jira task 
            logger.info("Routing to Jira restart handler")
            try:
                from jira.tasks import restart_collection as jira_restart_collection
                async_result = jira_restart_collection.apply_async(kwargs={
                    "task_pk": task_obj.id
                })
                logger.info(f"Jira restart task dispatched: {async_result.id}")
            except Exception as e:
                logger.error(f"Error dispatching Jira restart: {str(e)}")
                return Response({
                    "error": f"Error dispatching restart: {str(e)}",
                    "task_id": task_id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.error(f"Unknown task type: '{task_type}'")
            return Response({
                "error": f"Unknown task type: {task_type}",
                "task_id": task_id
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Restart scheduled",
            "celery_task_id": async_result.id,
            "resume_from": resume_from.isoformat() if resume_from else None,
            "status_endpoint": request.build_absolute_uri(f"/api/jobs/tasks/{task_obj.task_id}/"),
            "db_task_pk": task_obj.id
        }, status=status.HTTP_202_ACCEPTED)
