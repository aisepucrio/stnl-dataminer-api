from django.contrib import admin
from .models import (
    StackQuestion,
    StackAnswer,
    StackComment,
    StackTag,
    StackUser,
    StackBadge,
    StackCollective,
    StackQuestionTag,
    StackUserBadge,
    StackCollectiveTag,
    StackCollectiveUser,
    StackTagSynonym
)

@admin.register(StackQuestion)
class StackQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_id', 'title', 'creation_date', 'score', 'view_count', 'answer_count', 'is_answered')
    search_fields = ('title', 'body')
    list_filter = ('is_answered', 'creation_date', 'content_license')
    readonly_fields = ('question_id', 'time_mined')

@admin.register(StackAnswer)
class StackAnswerAdmin(admin.ModelAdmin):
    list_display = ('answer_id', 'question', 'score', 'is_accepted', 'creation_date')
    search_fields = ('body', 'title')
    list_filter = ('is_accepted', 'creation_date', 'content_license')
    readonly_fields = ('answer_id', 'time_mined')

@admin.register(StackComment)
class StackCommentAdmin(admin.ModelAdmin):
    list_display = ('comment_id', 'post_type', 'post_id', 'score', 'creation_date')
    search_fields = ('body',)
    list_filter = ('post_type', 'creation_date', 'content_license')
    readonly_fields = ('comment_id', 'time_mined')

@admin.register(StackTag)
class StackTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'count', 'is_moderator_only', 'is_required', 'last_activity_date')
    search_fields = ('name',)
    list_filter = ('is_moderator_only', 'is_required', 'has_synonyms')
    readonly_fields = ('name', 'last_sync')

@admin.register(StackUser)
class StackUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'display_name', 'reputation', 'user_type', 'creation_date')
    search_fields = ('display_name', 'about_me')
    list_filter = ('user_type', 'is_employee', 'creation_date')
    readonly_fields = ('user_id',)

@admin.register(StackBadge)
class StackBadgeAdmin(admin.ModelAdmin):
    list_display = ('badge_id', 'name', 'badge_type', 'rank')
    search_fields = ('name', 'description')
    list_filter = ('badge_type', 'rank')

@admin.register(StackCollective)
class StackCollectiveAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'last_sync')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'last_sync')

# Register the through models
admin.site.register(StackQuestionTag)
admin.site.register(StackUserBadge)
admin.site.register(StackCollectiveTag)
admin.site.register(StackCollectiveUser)
admin.site.register(StackTagSynonym) 