from rest_framework import serializers
from .models import JiraIssue

class JiraIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssue
        fields = '__all__'

class JiraIssueCollectSerializer(serializers.Serializer):
    jira_domain = serializers.CharField()
    project_key = serializers.CharField()
    issuetypes = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    start_date = serializers.CharField(required=False, allow_null=True)
    end_date = serializers.CharField(required=False, allow_null=True)