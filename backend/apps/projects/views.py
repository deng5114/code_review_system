import os
import shutil

from django.conf import settings
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.projects.models import Project, ProjectFile
from apps.projects.serializers import (
    FileContentSerializer,
    ProjectFileSerializer,
    ProjectSerializer,
    ProjectUploadSerializer,
)
from apps.projects.services.file_filter import FileFilter
from apps.projects.services.project_detector import ProjectDetector
from apps.projects.services.zip_parser import (
    PathTraversalError,
    ZipBombError,
    ZipParseError,
    ZipParser,
)


class ProjectViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_parsers(self):
        if getattr(self, "action", None) == "create":
            return [MultiPartParser()]
        return super().get_parsers()

    def create(self, request, *args, **kwargs):
        """上传并解析项目压缩包"""
        serializer = ProjectUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        upload_file = serializer.validated_data["file"]

        project = Project.objects.create(name=name, status="uploading")

        # 保存上传文件
        project.upload_file = upload_file
        project.save()

        try:
            project.status = "parsing"
            project.save()

            # 解析压缩包
            parser = ZipParser()
            output_dir = os.path.join(settings.MEDIA_ROOT, "extracted", str(project.id))
            result = parser.parse(project.upload_file.path, output_dir)

            # 过滤文件
            file_filter = FileFilter()
            filtered_files = file_filter.filter_files(result.file_list, result.extract_dir)

            # 检测项目类型
            detector = ProjectDetector()
            detection = detector.detect(result.extract_dir)

            # 更新项目信息
            project.project_type = detection.project_type
            project.detected_languages = detection.detected_languages
            project.detected_frameworks = detection.detected_frameworks
            project.total_files = len(filtered_files)
            project.total_lines = sum(f.line_count for f in filtered_files)
            project.file_path = result.extract_dir
            project.status = "ready"
            project.save()

            # 保存文件记录
            with transaction.atomic():
                for ff in filtered_files:
                    full_path = os.path.join(result.extract_dir, ff.path)
                    content = ""
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except OSError:
                        pass

                    ProjectFile.objects.create(
                        project=project,
                        file_path=ff.path,
                        language=ff.language,
                        line_count=ff.line_count,
                        content=content,
                        is_vendor=ff.is_vendor,
                        is_generated=ff.is_generated,
                        file_size=ff.file_size,
                    )

        except (ZipParseError, ZipBombError, PathTraversalError) as e:
            project.status = "error"
            project.error_message = str(e)
            project.save()
            return Response(
                {"success": False, "error": {"code": "PARSE_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            project.status = "error"
            project.error_message = str(e)
            project.save()
            return Response(
                {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "项目解析失败"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"success": True, "data": ProjectSerializer(project).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def files(self, request, pk=None):
        """获取项目的文件列表"""
        project = self.get_object()
        files = project.files.all()
        serializer = ProjectFileSerializer(files, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["get"], url_path="files/(?P<file_id>[^/.]+)")
    def file_content(self, request, pk=None, file_id=None):
        """获取项目单个文件的内容"""
        project = self.get_object()
        try:
            pf = project.files.get(id=file_id)
        except ProjectFile.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "文件不存在"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FileContentSerializer({
            "path": pf.file_path,
            "language": pf.language,
            "content": pf.content,
            "line_count": pf.line_count,
        })
        return Response({"success": True, "data": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})

        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        # 清理解压目录
        extract_dir = os.path.join(settings.MEDIA_ROOT, "extracted", str(project.id))
        if os.path.isdir(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        project.delete()
        return Response(
            {"success": True, "data": {"message": "项目已删除"}},
            status=status.HTTP_200_OK,
        )
