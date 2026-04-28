from django.conf import settings
from django.db import models

from apps.common.models import TimestampMixin, UUIDMixin


class ProjectStatus(models.TextChoices):
    UPLOADING = "uploading", "上传中"
    PARSING = "parsing", "解析中"
    READY = "ready", "就绪"
    ERROR = "error", "错误"


class ProjectType(models.TextChoices):
    NODEJS = "nodejs", "Node.js"
    PYTHON = "python", "Python"
    GO = "go", "Go"
    RUST = "rust", "Rust"
    JAVA = "java", "Java"
    TYPESCRIPT = "typescript", "TypeScript"
    UNKNOWN = "unknown", "未知"


class Project(UUIDMixin, TimestampMixin):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="所属用户",
    )
    name = models.CharField(max_length=255, verbose_name="项目名称")
    upload_file = models.FileField(
        upload_to="uploads/projects/%Y/%m/%d/",
        null=True,
        blank=True,
        verbose_name="上传文件",
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.UPLOADING,
        verbose_name="状态",
    )
    project_type = models.CharField(
        max_length=50,
        choices=ProjectType.choices,
        default=ProjectType.UNKNOWN,
        verbose_name="项目类型",
    )
    detected_languages = models.JSONField(default=dict, verbose_name="语言分布")
    detected_frameworks = models.JSONField(default=list, verbose_name="检测到的框架")
    total_files = models.IntegerField(default=0, verbose_name="文件总数")
    total_lines = models.IntegerField(default=0, verbose_name="代码行总数")
    file_path = models.CharField(
        max_length=512, null=True, blank=True, verbose_name="解压根目录"
    )
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")

    class Meta:
        db_table = "projects_project"
        verbose_name = "项目"
        verbose_name_plural = "项目"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


class ProjectFile(UUIDMixin, TimestampMixin):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="所属项目",
    )
    file_path = models.CharField(max_length=1024, verbose_name="相对文件路径")
    language = models.CharField(max_length=30, blank=True, verbose_name="编程语言")
    line_count = models.IntegerField(default=0, verbose_name="代码行数")
    content = models.TextField(blank=True, verbose_name="文件内容")
    is_vendor = models.BooleanField(default=False, verbose_name="第三方代码")
    is_generated = models.BooleanField(default=False, verbose_name="生成代码")
    file_size = models.IntegerField(default=0, verbose_name="文件大小(字节)")

    class Meta:
        db_table = "projects_projectfile"
        verbose_name = "项目文件"
        verbose_name_plural = "项目文件"
        unique_together = [["project", "file_path"]]

    def __str__(self) -> str:
        return f"{self.project.name}/{self.file_path}"


class ProjectStats(UUIDMixin, TimestampMixin):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="stats",
        verbose_name="所属项目",
    )
    language_distribution = models.JSONField(default=dict, verbose_name="语言分布")
    dependency_list = models.JSONField(default=list, verbose_name="依赖列表")
    framework_detected = models.CharField(
        max_length=100, blank=True, verbose_name="检测到的框架"
    )
    code_lines = models.IntegerField(default=0, verbose_name="有效代码行")
    comment_lines = models.IntegerField(default=0, verbose_name="注释行")
    blank_lines = models.IntegerField(default=0, verbose_name="空行")

    class Meta:
        db_table = "projects_projectstats"
        verbose_name = "项目统计"
        verbose_name_plural = "项目统计"

    def __str__(self) -> str:
        return f"{self.project.name} - 统计"
