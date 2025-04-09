from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['task_id', 'operation', 'repository', 'created_at', 'created_at_formatted', 'status', 'error']
    
    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S") 