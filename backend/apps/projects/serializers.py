from rest_framework import serializers

from apps.projects.models import Project, ProjectFile


class ProjectUploadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    file = serializers.FileField()

    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

    def validate_file(self, value):
        if value.size > self.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"文件大小不能超过 {self.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )
        return value


class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = [
            "id", "file_path", "language", "line_count",
            "is_vendor", "is_generated", "file_size", "created_at",
        ]
        read_only_fields = fields


class FileTreeNodeSerializer(serializers.Serializer):
    name = serializers.CharField()
    path = serializers.CharField()
    is_dir = serializers.BooleanField()
    children = serializers.ListField(child=serializers.DictField(), required=False)


class ProjectSerializer(serializers.ModelSerializer):
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "status", "project_type",
            "detected_languages", "detected_frameworks",
            "total_files", "total_lines",
            "error_message", "files_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "project_type",
            "detected_languages", "detected_frameworks",
            "total_files", "total_lines",
            "error_message", "files_count",
            "created_at", "updated_at",
        ]

    def get_files_count(self, obj: Project) -> int:
        return obj.files.count()


class FileContentSerializer(serializers.Serializer):
    path = serializers.CharField()
    language = serializers.CharField()
    content = serializers.CharField()
    line_count = serializers.IntegerField()
