from unittest.mock import MagicMock, patch

import pytest

from apps.ai.models import AIConfig
from apps.projects.models import Project, ProjectFile
from apps.reviews.models import Review, ReviewIssue, ReviewStatus
from apps.reviews.tasks import start_review_task


@pytest.fixture
def setup_review(db, user) -> Review:
    project = Project.objects.create(
        name="TestProject",
        owner=user,
        status="ready",
        project_type="python",
        detected_languages=["Python"],
        detected_frameworks=["django"],
        total_files=2,
        total_lines=30,
    )
    ProjectFile.objects.create(
        project=project,
        file_path="app.py",
        language="python",
        line_count=20,
        content="def hello():\n    pass\n",
    )
    config = AIConfig(
        owner=user,
        provider="openai",
        display_name="Test",
        model_name="gpt-4o",
        base_url="",
        is_default=True,
        is_active=True,
    )
    config.api_key = "sk-test-api-key-1234567890"
    config.save()

    review = Review.objects.create(
        project=project,
        status=ReviewStatus.PENDING,
        ai_model="",
        ai_provider="",
    )
    return review


@pytest.mark.django_db
class TestStartReviewTask:
    @patch("apps.reviews.tasks.ReviewEngine")
    def test_successful_review(self, MockEngine, setup_review):
        engine = MockEngine.return_value
        engine.run_review.return_value = {
            "status": "completed",
            "summary": "Found 1 issue.",
            "issues": [
                {
                    "file_path": "app.py",
                    "start_line": 1,
                    "end_line": 1,
                    "severity": "high",
                    "dimension": "security",
                    "title": "SQL Injection",
                    "description": "Input not sanitized",
                    "suggestion": "Use parameterized queries",
                    "code_snippet": "",
                    "fix_snippet": "",
                    "confidence": 0.9,
                },
            ],
            "stats": {
                "total": 1, "critical_count": 0, "high_count": 1,
                "medium_count": 0, "low_count": 0,
            },
        }

        start_review_task(str(setup_review.id))

        review = Review.objects.get(id=setup_review.id)
        assert review.status == ReviewStatus.COMPLETED
        assert review.total_issues == 1
        assert review.high_count == 1
        assert review.ai_model == "gpt-4o"
        assert review.summary == "Found 1 issue."
        assert review.started_at is not None
        assert review.completed_at is not None

        issues = ReviewIssue.objects.filter(review=review)
        assert issues.count() == 1
        assert issues.first().title == "SQL Injection"

    @patch("apps.reviews.tasks.ReviewEngine")
    def test_failed_review(self, MockEngine, setup_review):
        engine = MockEngine.return_value
        engine.run_review.return_value = {
            "status": "failed",
            "error_message": "API timeout",
            "issues": [],
            "summary": "",
            "stats": {"total": 0, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0},
        }

        start_review_task(str(setup_review.id))

        review = Review.objects.get(id=setup_review.id)
        assert review.status == ReviewStatus.FAILED
        assert "API timeout" in review.error_message

    def test_nonexistent_review(self, db):
        start_review_task("00000000-0000-0000-0000-000000000000")
        # Should not raise, just log and return

    @patch("apps.reviews.tasks.ReviewEngine")
    def test_no_ai_config(self, MockEngine, db, user):
        project = Project.objects.create(name="NoConfig", owner=user, status="ready")
        review = Review.objects.create(project=project, ai_model="", ai_provider="")

        start_review_task(str(review.id))

        review = Review.objects.get(id=review.id)
        assert review.status == ReviewStatus.FAILED
        assert "AI" in review.error_message

    @patch("apps.reviews.tasks.ReviewEngine")
    def test_progress_updated(self, MockEngine, setup_review):
        engine = MockEngine.return_value

        def fake_run_review(**kwargs):
            progress_cb = kwargs.get("progress_callback")
            if progress_cb:
                progress_cb(50, "Halfway")
            return {
                "status": "completed",
                "summary": "Done",
                "issues": [],
                "stats": {"total": 0, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0},
            }

        engine.run_review.side_effect = fake_run_review

        start_review_task(str(setup_review.id))

        review = Review.objects.get(id=setup_review.id)
        assert review.status == ReviewStatus.COMPLETED
        assert review.progress == 100
