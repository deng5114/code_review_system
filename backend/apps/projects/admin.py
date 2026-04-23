from django.contrib import admin

from .models import Project, ProjectFile, ProjectStats


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "project_type", "status", "total_files", "created_at"]
    list_filter = ["status", "project_type"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ["file_path", "language", "line_count", "is_vendor"]
    list_filter = ["language", "is_vendor", "is_generated"]
    search_fields = ["file_path"]


@admin.register(ProjectStats)
class ProjectStatsAdmin(admin.ModelAdmin):
    list_display = ["project", "framework_detected", "code_lines"]
    readonly_fields = ["created_at", "updated_at"]
