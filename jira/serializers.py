from rest_framework import serializers
from .models import JiraIssue, JiraIssueType

class JiraIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssue
        fields = '__all__'

class JiraIssueTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssueType
        fields = '__all__'