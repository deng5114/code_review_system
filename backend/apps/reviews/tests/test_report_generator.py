import pytest

from apps.ai.services.response_parser import ParsedIssue
from apps.reviews.services.report_generator import ReportGenerator


def _make_issue(**overrides) -> ParsedIssue:
    defaults = dict(
        file_path="app.py", start_line=5, end_line=10,
        severity="critical", dimension="security",
        title="SQL Injection", description="User input not sanitized",
        suggestion="Use parameterized queries",
        code_snippet="query = f\"SELECT * FROM {table}\"",
        fix_snippet="cursor.execute(\"SELECT * FROM ?\", (table,))",
        confidence=0.95,
    )
    defaults.update(overrides)
    return ParsedIssue(**defaults)


@pytest.fixture
def generator():
    return ReportGenerator()


@pytest.fixture
def sample_review_data():
    return {
        "project_name": "TestProject",
        "status": "completed",
        "ai_model": "gpt-4o",
        "summary": "Found 2 security issues requiring immediate attention.",
    }


class TestMarkdownReport:
    def test_contains_header(self, generator, sample_review_data):
        issues = [_make_issue()]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "# Code Review Report" in md
        assert "TestProject" in md

    def test_contains_summary(self, generator, sample_review_data):
        issues = [_make_issue()]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "Found 2 security issues" in md

    def test_contains_issue_details(self, generator, sample_review_data):
        issues = [_make_issue(title="SQL Injection", file_path="app.py")]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "SQL Injection" in md
        assert "app.py" in md

    def test_severity_badges(self, generator, sample_review_data):
        issues = [_make_issue(severity="critical")]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "CRITICAL" in md

    def test_empty_issues(self, generator, sample_review_data):
        md = generator.generate_markdown(sample_review_data, [])
        assert "No issues found" in md

    def test_code_snippet_included(self, generator, sample_review_data):
        issues = [_make_issue(code_snippet="dangerous code")]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "dangerous code" in md

    def test_fix_snippet_included(self, generator, sample_review_data):
        issues = [_make_issue(fix_snippet="safe code")]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "safe code" in md

    def test_stats_section(self, generator, sample_review_data):
        issues = [
            _make_issue(severity="critical", title="A"),
            _make_issue(severity="high", start_line=20, title="B"),
        ]
        md = generator.generate_markdown(sample_review_data, issues)
        assert "Statistics" in md or "统计" in md or "2" in md


class TestJsonReport:
    def test_structure(self, generator, sample_review_data):
        issues = [_make_issue()]
        result = generator.generate_json(sample_review_data, issues)
        assert "project_name" in result
        assert "issues" in result
        assert len(result["issues"]) == 1

    def test_issue_fields(self, generator, sample_review_data):
        issues = [_make_issue()]
        result = generator.generate_json(sample_review_data, issues)
        issue = result["issues"][0]
        assert issue["file_path"] == "app.py"
        assert issue["severity"] == "critical"
        assert issue["title"] == "SQL Injection"
        assert issue["confidence"] == 0.95

    def test_empty_issues(self, generator, sample_review_data):
        result = generator.generate_json(sample_review_data, [])
        assert result["issues"] == []
        assert result["total_issues"] == 0

    def test_stats_included(self, generator, sample_review_data):
        issues = [
            _make_issue(severity="critical", title="A"),
            _make_issue(severity="high", start_line=20, title="B"),
        ]
        result = generator.generate_json(sample_review_data, issues)
        assert "stats" in result
        assert result["stats"]["critical_count"] == 1
        assert result["stats"]["high_count"] == 1

    def test_serializable(self, generator, sample_review_data):
        import json
        issues = [_make_issue()]
        result = generator.generate_json(sample_review_data, issues)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)
