import logging
from datetime import datetime, timezone

from celery import shared_task

from apps.reviews.services.review_engine import ReviewEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def start_review_task(self, review_id: str) -> None:
    from django.db import transaction

    from apps.ai.models import AIConfig
    from apps.ai.services.llm_adapter import LLMConfig
    from apps.ai.services.llm_call_manager import LLMCallManager
    from apps.projects.models import ProjectFile
    from apps.reviews.models import Review, ReviewIssue, ReviewStatus

    try:
        review = Review.objects.select_related("project").get(id=review_id)
    except Review.DoesNotExist:
        logger.error("Review %s not found", review_id)
        return

    try:
        # Mark as running
        review.status = ReviewStatus.RUNNING
        review.started_at = datetime.now(timezone.utc)
        review.progress = 0
        review.save(update_fields=["status", "started_at", "progress", "updated_at"])

        # Load project files
        project = review.project
        files_qs = ProjectFile.objects.filter(project=project).values(
            "file_path", "language", "line_count", "content",
            "is_vendor", "is_generated",
        )
        files = [
            {
                "path": f["file_path"],
                "language": f["language"],
                "line_count": f["line_count"],
                "content": f["content"],
                "is_vendor": f["is_vendor"],
                "is_generated": f["is_generated"],
            }
            for f in files_qs
        ]

        # Load AI config
        ai_config_obj = AIConfig.objects.filter(is_active=True).order_by(
            "-is_default", "created_at"
        ).first()
        if not ai_config_obj:
            raise ValueError("No active AI configuration found")

        primary_llm_config = LLMConfig.from_ai_config(ai_config_obj)

        fallback_configs = LLMCallManager.build_fallback_chain(
            list(
                AIConfig.objects.filter(
                    is_active=True, fallback_enabled=True,
                ).exclude(pk=ai_config_obj.pk).order_by("-priority")[:5]
            )
        )

        # Run review
        def on_progress(pct, msg):
            try:
                review.progress = pct
                review.save(update_fields=["progress", "updated_at"])
            except Exception:
                logger.warning("Failed to update progress for review %s", review_id)

        engine = ReviewEngine()
        result = engine.run_review(
            project_type=project.project_type or "unknown",
            primary_language=(project.detected_languages or ["unknown"])[0] if project.detected_languages else "unknown",
            frameworks=project.detected_frameworks or [],
            files=files,
            ai_config=primary_llm_config,
            fallback_configs=fallback_configs,
            custom_instructions=review.custom_instructions,
            progress_callback=on_progress,
        )

        # Save results
        review.ai_model = ai_config_obj.model_name
        review.ai_provider = ai_config_obj.provider

        if result["status"] == "completed":
            review.status = ReviewStatus.COMPLETED
            review.summary = result.get("summary", "")
            review.total_issues = result["stats"]["total"]
            review.critical_count = result["stats"]["critical_count"]
            review.high_count = result["stats"]["high_count"]
            review.medium_count = result["stats"]["medium_count"]
            review.low_count = result["stats"]["low_count"]
            review.completed_at = datetime.now(timezone.utc)
            review.progress = 100

            with transaction.atomic():
                for issue_data in result.get("issues", []):
                    ReviewIssue.objects.create(
                        review=review,
                        file_path=issue_data["file_path"],
                        start_line=issue_data["start_line"],
                        end_line=issue_data["end_line"],
                        severity=issue_data["severity"],
                        dimension=issue_data["dimension"],
                        title=issue_data["title"],
                        description=issue_data["description"],
                        suggestion=issue_data.get("suggestion", ""),
                        code_snippet=issue_data.get("code_snippet", ""),
                        fix_snippet=issue_data.get("fix_snippet", ""),
                        confidence=issue_data.get("confidence", 1.0),
                    )
                review.save(update_fields=[
                    "status", "ai_model", "ai_provider", "summary",
                    "total_issues", "critical_count", "high_count",
                    "medium_count", "low_count", "completed_at",
                    "progress", "updated_at",
                ])
        else:
            review.status = ReviewStatus.FAILED
            review.error_message = result.get("error_message", "Unknown error")
            review.save(update_fields=[
                "status", "error_message", "ai_model",
                "ai_provider", "updated_at",
            ])

    except Exception as e:
        logger.exception("Review task failed: %s", e)
        try:
            review.status = ReviewStatus.FAILED
            review.error_message = str(e)[:2000]
            review.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            logger.exception("Failed to update review status")
