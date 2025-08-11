from django.contrib import admin
from .models import Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'platform', 'owner', 'name', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['full_name', 'owner', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'owner', 'name', 'platform')
        }),
        ('Details', {
            'fields': ('url', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )