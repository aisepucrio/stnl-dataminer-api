from rest_framework import serializers

from .models import JiraIssue, JiraProject, JiraUser, JiraSprint, JiraComment, JiraChecklist, JiraIssueType, JiraIssueLink, JiraCommit, JiraActivityLog, JiraHistory, JiraHistoryItem

class JiraIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssue
        fields = '__all__'

class JiraProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraProject
        fields = '__all__'

class JiraUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraUser
        fields = '__all__'

class JiraSprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraSprint
        fields = '__all__'

class JiraCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraComment
        fields = '__all__'

class JiraChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraChecklist
        fields = '__all__'

class JiraIssueTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssueType
        fields = '__all__'

class JiraIssueLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraIssueLink
        fields = '__all__'

class JiraCommitSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraCommit
        fields = '__all__'

class JiraActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraActivityLog
        fields = '__all__'

class JiraHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraHistory
        fields = '__all__'

class JiraHistoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiraHistoryItem
        fields = '__all__'

class JiraIssueCollectSerializer(serializers.Serializer):
    jira_domain = serializers.CharField()
    project_key = serializers.CharField()
    issuetypes = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    start_date = serializers.CharField(required=False, allow_null=True)
    end_date = serializers.CharField(required=False, allow_null=True)