from rest_framework import serializers
from .models import JiraIssue

class JiraIssueSerializer(serializers.ModelSerializer):
    history_formatted = serializers.SerializerMethodField()
    activity_log_formatted = serializers.SerializerMethodField()
    checklist_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = JiraIssue
        fields = '__all__'
    
    def get_history_formatted(self, obj):
        """Formata o histórico para exibição"""
        if not obj.history:
            return []
        
        formatted_history = []
        for item in obj.history:
            formatted_item = {
                'id': item.get('id'),
                'author': item.get('author'),
                'created': item.get('created'),
                'changes': []
            }
            
            for change in item.get('items', []):
                formatted_item['changes'].append({
                    'field': change.get('field'),
                    'from': change.get('fromString') or change.get('from'),
                    'to': change.get('toString') or change.get('to')
                })
            
            formatted_history.append(formatted_item)
        
        return formatted_history
    
    def get_activity_log_formatted(self, obj):
        """Formata o registro de atividades para exibição similar à interface do Jira"""
        if not obj.activity_log:
            return []
        
        formatted_activities = []
        for activity in obj.activity_log:
            activity_type = activity.get('type')
            created_date = activity.get('created')
            
            formatted_activity = {
                'author': activity.get('author'),
                'created': created_date,
                'description': activity.get('description'),
                'type': activity_type,
            }
            
            # Adicionar informações específicas baseadas no tipo
            if activity_type == 'status_change':
                formatted_activity.update({
                    'from_status': activity.get('from'),
                    'to_status': activity.get('to'),
                })
            elif activity_type == 'resolution_change':
                formatted_activity.update({
                    'from_resolution': activity.get('from'),
                    'to_resolution': activity.get('to'),
                })
            elif activity_type == 'estimate_change':
                formatted_activity.update({
                    'from_estimate': activity.get('from'),
                    'to_estimate': activity.get('to'),
                })
            elif activity_type == 'time_logged':
                formatted_activity.update({
                    'time_spent': activity.get('time'),
                })
            
            formatted_activities.append(formatted_activity)
        
        return formatted_activities
    
    def get_checklist_formatted(self, obj):
        """Formata o checklist para exibição"""
        if not obj.checklist:
            return []
        
        formatted_checklist = []
        for item in obj.checklist:
            formatted_item = {
                'text': item.get('text'),
                'status': item.get('status'),
                'completed': item.get('completed', False),
                'completed_by': item.get('completed_by'),
                'created': item.get('created'),
                'updated': item.get('updated')
            }
            formatted_checklist.append(formatted_item)
        
        return formatted_checklist

class JiraIssueCollectSerializer(serializers.Serializer):
    jira_domain = serializers.CharField()
    project_key = serializers.CharField()
    issuetypes = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    start_date = serializers.CharField(required=False, allow_null=True)
    end_date = serializers.CharField(required=False, allow_null=True)