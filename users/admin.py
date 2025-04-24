from django.contrib import admin
from .models import Project, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'has_api_key', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username')
    date_hierarchy = 'created_at'

    def has_api_key(self, obj):
        return bool(obj.openai_api_key)
    has_api_key.boolean = True
    has_api_key.short_description = 'Has API Key'

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'description', 'user__email', 'user__username')
    date_hierarchy = 'created_at'
