from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimestampMixin, UUIDMixin
from apps.projects.models import Project


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "等待中"
    RUNNING = "running", "运行中"
    COMPLETED = "completed", "已完成"
    FAILED = "failed", "失败"


class Severity(models.TextChoices):
    CRITICAL = "critical", "关键"
    HIGH = "high", "高"
    MEDIUM = "medium", "中"
    LOW = "low", "低"


class Dimension(models.TextChoices):
    SECURITY = "security", "安全性"
    CORRECTNESS = "correctness", "正确性"
    PERFORMANCE = "performance", "性能"
    MAINTAINABILITY = "maintainability", "可维护性"
    TYPE_SAFETY = "type_safety", "类型安全"
    COMPLETENESS = "completeness", "完整性"
    BEST_PRACTICES = "best_practices", "最佳实践"


class Review(UUIDMixin, TimestampMixin):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="审查的项目",
    )
    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        verbose_name="状态",
    )
    ai_model = models.CharField(max_length=100, verbose_name="AI 模型")
    ai_provider = models.CharField(max_length=50, verbose_name="AI 提供商")
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="进度",
    )
    total_issues = models.IntegerField(default=0, verbose_name="问题总数")
    critical_count = models.IntegerField(default=0, verbose_name="关键问题数")
    high_count = models.IntegerField(default=0, verbose_name="高优先级数")
    medium_count = models.IntegerField(default=0, verbose_name="中优先级数")
    low_count = models.IntegerField(default=0, verbose_name="低优先级数")
    summary = models.TextField(blank=True, verbose_name="总体评估")
    error_message = models.TextField(blank=True, null=True, verbose_name="失败原因")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="完成时间"
    )
    custom_instructions = models.TextField(
        blank=True, verbose_name="自定义审查指令"
    )

    class Meta:
        db_table = "reviews_review"
        verbose_name = "代码审查"
        verbose_name_plural = "代码审查"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Review {self.id} - {self.project.name}"


class ReviewIssue(UUIDMixin, TimestampMixin):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="issues",
        verbose_name="所属审查",
    )
    file_path = models.CharField(max_length=1024, verbose_name="文件路径")
    start_line = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="起始行号",
    )
    end_line = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="结束行号",
    )
    severity = models.CharField(
        max_length=20, choices=Severity.choices, verbose_name="严重性"
    )
    dimension = models.CharField(
        max_length=30, choices=Dimension.choices, verbose_name="审查维度"
    )
    title = models.CharField(max_length=500, verbose_name="问题标题")
    description = models.TextField(verbose_name="问题描述")
    suggestion = models.TextField(blank=True, verbose_name="修复建议")
    code_snippet = models.TextField(blank=True, verbose_name="问题代码")
    fix_snippet = models.TextField(blank=True, verbose_name="修复代码")
    confidence = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="置信度",
    )

    class Meta:
        db_table = "reviews_reviewissue"
        verbose_name = "审查问题"
        verbose_name_plural = "审查问题"
        ordering = ["file_path", "start_line"]

    def __str__(self) -> str:
        return f"[{self.get_severity_display()}] {self.title}"
