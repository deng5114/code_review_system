from django.contrib import admin

from .models import Review, ReviewIssue


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "project",
        "status",
        "progress",
        "total_issues",
        "created_at",
    ]
    list_filter = ["status", "ai_provider"]
    search_fields = ["project__name", "ai_model"]
    readonly_fields = ["created_at", "updated_at", "started_at", "completed_at"]


@admin.register(ReviewIssue)
class ReviewIssueAdmin(admin.ModelAdmin):
    list_display = ["title", "severity", "dimension", "file_path", "start_line"]
    list_filter = ["severity", "dimension"]
    search_fields = ["title", "file_path"]
