from rest_framework import serializers

from .models import (
    JiraIssue, JiraProject, JiraUser, JiraSprint, JiraComment, JiraChecklist,
    JiraIssueType, JiraIssueLink, JiraCommit, JiraActivityLog, JiraHistory, JiraHistoryItem
)


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
    # Validação de datas já no serializer (YYYY-MM-DD)
    start_date = serializers.DateField(
        required=False, allow_null=True, input_formats=['%Y-%m-%d']
    )
    end_date = serializers.DateField(
        required=False, allow_null=True, input_formats=['%Y-%m-%d']
    )

    def validate(self, attrs):
        sd = attrs.get("start_date")
        ed = attrs.get("end_date")
        if sd and ed and ed < sd:
            raise serializers.ValidationError("end_date must be >= start_date.")
        return attrs


class JiraExportDataSerializer(serializers.Serializer):
    # Qual tabela/Jira model exportar (ajuste a lista conforme o que você quer suportar)
    table = serializers.ChoiceField(
        choices=[
            'jiraissue',
            'jiracomment',
            'jirahistory',
            'jirahistoryitem',
            'jiraactivitylog',
            'jiracommit',
            'jirasprint',
            'jiraproject',
            'jirauser',
            'jiraissuetype',
            'jiraissuelink',
            'jirachecklist',
        ],
        help_text="Table name to export"
    )

    # IDs explícitos (opcional)
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Optional explicit IDs to export"
    )

    # Formato de saída
    format = serializers.ChoiceField(
        choices=['json', 'csv'],
        default='csv',
        help_text="Output format"
    )

    # Seleção de colunas (CSV)
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Optional: limit CSV columns to this list of field names"
    )

    # --- Filtros simples (mapearemos na view apenas se os campos existirem no model) ---
    project = serializers.CharField(required=False, help_text="Filter by project key/name")
    status = serializers.CharField(required=False, help_text="Issue status")
    reporter = serializers.CharField(required=False, help_text="Reporter")
    assignee = serializers.CharField(required=False, help_text="Assignee")
    issue_type = serializers.CharField(required=False, help_text="Issue type")
    sprint = serializers.CharField(required=False, help_text="Sprint name/ID")
    priority = serializers.CharField(required=False, help_text="Priority")

    # --- Filtros de data no BODY (mesma convenção do Git) ---
    date = serializers.DateField(required=False, help_text="Single day filter (UTC date)")
    start_date = serializers.DateTimeField(required=False, help_text="Start datetime (UTC, inclusive)")
    end_date = serializers.DateTimeField(required=False, help_text="End datetime (UTC, inclusive)")

    def validate(self, data):
        # Garantir exclusividade: usar 'date' OU 'start_date'/'end_date'
        if data.get("date") and (data.get("start_date") or data.get("end_date")):
            raise serializers.ValidationError("Use either 'date' OR 'start_date'/'end_date'.")
        return data
