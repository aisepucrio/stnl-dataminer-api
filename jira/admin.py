from django.contrib import admin
from .models import (
    JiraIssue, JiraProject, JiraUser, JiraComment, JiraChecklist,
    JiraIssueType, JiraSprint, JiraIssueLink, JiraCommit,
    JiraActivityLog, JiraHistory, JiraHistoryItem
)

# Register your models here.
admin.site.register(JiraIssue)
admin.site.register(JiraProject)
admin.site.register(JiraUser)
admin.site.register(JiraComment)
admin.site.register(JiraChecklist)
admin.site.register(JiraIssueType)
admin.site.register(JiraSprint)
admin.site.register(JiraIssueLink)
admin.site.register(JiraCommit)
admin.site.register(JiraActivityLog)
admin.site.register(JiraHistory)
admin.site.register(JiraHistoryItem)

