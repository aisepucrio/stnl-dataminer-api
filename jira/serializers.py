from rest_framework import serializers
from .models import JiraIssue

class JiraIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssue
        fields = '__all__'