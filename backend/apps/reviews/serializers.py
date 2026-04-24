from rest_framework import serializers

from apps.reviews.models import Review, ReviewIssue


class ReviewIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewIssue
        fields = [
            "id", "file_path", "start_line", "end_line",
            "severity", "dimension", "title", "description",
            "suggestion", "code_snippet", "fix_snippet",
            "confidence", "created_at",
        ]
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "project", "project_name", "status",
            "ai_model", "ai_provider", "progress",
            "total_issues", "critical_count", "high_count",
            "medium_count", "low_count",
            "summary", "error_message",
            "custom_instructions",
            "started_at", "completed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "ai_model", "ai_provider", "progress",
            "total_issues", "critical_count", "high_count",
            "medium_count", "low_count", "summary", "error_message",
            "started_at", "completed_at", "created_at", "updated_at",
        ]


class CreateReviewSerializer(serializers.Serializer):
    custom_instructions = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
