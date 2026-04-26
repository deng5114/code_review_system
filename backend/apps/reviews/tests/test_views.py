from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.models import AIConfig
from apps.projects.models import Project
from apps.reviews.models import Review, ReviewIssue, ReviewStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def project(db):
    return Project.objects.create(
        name="TestProject",
        status="ready",
        project_type="python",
        detected_languages=["Python"],
        detected_frameworks=["django"],
        total_files=2,
        total_lines=30,
    )


@pytest.fixture
def review(project):
    return Review.objects.create(
        project=project,
        status=ReviewStatus.COMPLETED,
        ai_model="gpt-4o",
        ai_provider="openai",
        progress=100,
        total_issues=2,
        critical_count=1,
        high_count=1,
        medium_count=0,
        low_count=0,
        summary="Found 2 issues.",
    )


@pytest.fixture
def review_with_issues(review):
    ReviewIssue.objects.create(
        review=review,
        file_path="app.py",
        start_line=5,
        end_line=10,
        severity="critical",
        dimension="security",
        title="SQL Injection",
        description="Input not sanitized",
        suggestion="Use parameterized queries",
        code_snippet="query = f\"SELECT * FROM {table}\"",
        fix_snippet="cursor.execute(\"SELECT * FROM ?\", (table,))",
        confidence=0.95,
    )
    ReviewIssue.objects.create(
        review=review,
        file_path="utils.py",
        start_line=3,
        end_line=3,
        severity="high",
        dimension="performance",
        title="N+1 Query",
        description="Loop contains DB query",
        suggestion="Batch the query",
        confidence=0.8,
    )
    return review


@pytest.mark.django_db
class TestCreateReview:
    @patch("apps.reviews.views.transaction.on_commit", side_effect=lambda cb: cb())
    @patch("apps.reviews.views.start_review_task")
    def test_create_review(self, mock_task, mock_on_commit, api_client, project):
        resp = api_client.post(
            "/api/reviews/",
            {"project_id": str(project.id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["success"] is True
        assert resp.data["data"]["status"] == "pending"
        assert resp.data["data"]["project"] == project.id
        mock_task.delay.assert_called_once()

    @patch("apps.reviews.views.transaction.on_commit", side_effect=lambda cb: cb())
    @patch("apps.reviews.views.start_review_task")
    def test_create_with_custom_instructions(self, mock_task, mock_on_commit, api_client, project):
        resp = api_client.post(
            "/api/reviews/",
            {"project_id": str(project.id), "custom_instructions": "Focus on security"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        review = Review.objects.get(id=resp.data["data"]["id"])
        assert review.custom_instructions == "Focus on security"

    def test_create_missing_project_id(self, api_client):
        resp = api_client.post("/api/reviews/", {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_nonexistent_project(self, api_client):
        resp = api_client.post(
            "/api/reviews/",
            {"project_id": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestListReviews:
    def test_list_reviews(self, api_client, review):
        resp = api_client.get("/api/reviews/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        assert len(resp.data["data"]) >= 1

    def test_filter_by_project(self, api_client, review, project):
        resp = api_client.get(f"/api/reviews/?project_id={project.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert all(r["project"] == project.id for r in resp.data["data"])


@pytest.mark.django_db
class TestRetrieveReview:
    def test_retrieve_review(self, api_client, review):
        resp = api_client.get(f"/api/reviews/{review.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["ai_model"] == "gpt-4o"
        assert resp.data["data"]["total_issues"] == 2
        assert resp.data["data"]["project_name"] == "TestProject"

    def test_retrieve_nonexistent(self, api_client):
        resp = api_client.get("/api/reviews/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReviewIssues:
    def test_list_issues(self, api_client, review_with_issues):
        resp = api_client.get(f"/api/reviews/{review_with_issues.id}/issues/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 2

    def test_filter_by_severity(self, api_client, review_with_issues):
        resp = api_client.get(f"/api/reviews/{review_with_issues.id}/issues/?severity=critical")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["severity"] == "critical"

    def test_filter_by_dimension(self, api_client, review_with_issues):
        resp = api_client.get(f"/api/reviews/{review_with_issues.id}/issues/?dimension=performance")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_filter_by_file_path(self, api_client, review_with_issues):
        resp = api_client.get(f"/api/reviews/{review_with_issues.id}/issues/?file_path=utils")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_filter_by_multiple_severities(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?severity=critical,high"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 2

    def test_filter_by_severity_with_trailing_comma(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?severity=critical,"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["severity"] == "critical"

    def test_filter_by_multiple_dimensions(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?dimension=security,performance"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 2

    def test_filter_empty_severity(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?severity="
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 2

    def test_search_by_title(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?search=SQL"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["title"] == "SQL Injection"

    def test_search_by_description(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?search=sanitized"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_search_case_insensitive(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?search=sql"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_search_no_results(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?search=nonexistent"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 0

    def test_combined_severity_and_search(self, api_client, review_with_issues):
        resp = api_client.get(
            f"/api/reviews/{review_with_issues.id}/issues/?severity=critical&search=SQL"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["severity"] == "critical"

    def test_empty_issues(self, api_client, review):
        resp = api_client.get(f"/api/reviews/{review.id}/issues/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 0


@pytest.mark.django_db
class TestReviewReport:
    def test_json_report(self, api_client, review_with_issues):
        resp = api_client.get(f"/api/reviews/{review_with_issues.id}/report/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["total_issues"] == 2
        assert len(resp.data["data"]["issues"]) == 2

    def test_markdown_report(self, api_client, review_with_issues):
        resp = api_client.get(f"/api/reviews/{review_with_issues.id}/report/?output=markdown")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["format"] == "markdown"
        assert "SQL Injection" in resp.data["data"]["content"]
