import pytest

from apps.ai.services.response_parser import ParsedIssue
from apps.reviews.services.result_aggregator import AggregatedResult, ResultAggregator


def _make_issue(
    file_path: str = "app.py",
    start_line: int = 1,
    end_line: int = 5,
    severity: str = "high",
    dimension: str = "security",
    title: str = "Issue",
    description: str = "A problem",
    suggestion: str = "Fix it",
    confidence: float = 0.9,
) -> ParsedIssue:
    return ParsedIssue(
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        severity=severity,
        dimension=dimension,
        title=title,
        description=description,
        suggestion=suggestion,
        code_snippet=None,
        fix_snippet=None,
        confidence=confidence,
    )


@pytest.fixture
def aggregator():
    return ResultAggregator()


class TestDeduplicate:
    def test_removes_exact_duplicates(self, aggregator):
        issues = [_make_issue(title="SQL injection"), _make_issue(title="SQL injection")]
        result = aggregator.aggregate(issues)
        assert len(result.issues) == 1

    def test_merges_overlapping_lines(self, aggregator):
        issues = [
            _make_issue(start_line=5, end_line=10, title="Bug A"),
            _make_issue(start_line=8, end_line=15, title="Bug A"),
        ]
        result = aggregator.aggregate(issues)
        assert len(result.issues) == 1
        assert result.issues[0].start_line == 5
        assert result.issues[0].end_line == 15

    def test_keeps_different_issues_in_same_file(self, aggregator):
        issues = [
            _make_issue(start_line=1, end_line=5, title="Bug A"),
            _make_issue(start_line=20, end_line=25, title="Bug B"),
        ]
        result = aggregator.aggregate(issues)
        assert len(result.issues) == 2

    def test_different_files_not_deduplicated(self, aggregator):
        issues = [
            _make_issue(file_path="a.py", title="Bug"),
            _make_issue(file_path="b.py", title="Bug"),
        ]
        result = aggregator.aggregate(issues)
        assert len(result.issues) == 2


class TestConfidenceDowngrade:
    def test_low_confidence_severity_downgraded(self, aggregator):
        issues = [_make_issue(severity="critical", confidence=0.3)]
        result = aggregator.aggregate(issues)
        assert result.issues[0].severity == "high"

    def test_medium_confidence_kept(self, aggregator):
        issues = [_make_issue(severity="high", confidence=0.6)]
        result = aggregator.aggregate(issues)
        assert result.issues[0].severity == "high"

    def test_threshold_configurable(self):
        agg = ResultAggregator(confidence_threshold=0.8)
        issues = [_make_issue(severity="critical", confidence=0.7)]
        result = agg.aggregate(issues)
        assert result.issues[0].severity == "high"


class TestStats:
    def test_severity_counts(self, aggregator):
        issues = [
            _make_issue(severity="critical", title="SQL injection"),
            _make_issue(severity="critical", start_line=20, end_line=25, title="XSS"),
            _make_issue(severity="high", title="Logic error"),
            _make_issue(severity="low", title="Style issue"),
        ]
        result = aggregator.aggregate(issues)
        assert result.stats["critical_count"] == 2
        assert result.stats["high_count"] == 1
        assert result.stats["medium_count"] == 0
        assert result.stats["low_count"] == 1
        assert result.stats["total"] == 4

    def test_dimension_counts(self, aggregator):
        issues = [
            _make_issue(dimension="security", title="Bug A"),
            _make_issue(dimension="security", start_line=20, title="Bug B"),
            _make_issue(dimension="performance", title="Bug C"),
        ]
        result = aggregator.aggregate(issues)
        assert result.stats["by_dimension"]["security"] == 2
        assert result.stats["by_dimension"]["performance"] == 1

    def test_file_counts(self, aggregator):
        issues = [
            _make_issue(file_path="a.py", title="Bug A"),
            _make_issue(file_path="a.py", start_line=20, title="Bug B"),
            _make_issue(file_path="b.py", title="Bug C"),
        ]
        result = aggregator.aggregate(issues)
        assert result.stats["by_file"]["a.py"] == 2
        assert result.stats["by_file"]["b.py"] == 1

    def test_empty_issues(self, aggregator):
        result = aggregator.aggregate([])
        assert result.stats["total"] == 0
        assert len(result.issues) == 0


class TestAggregatedResult:
    def test_result_fields(self, aggregator):
        issues = [_make_issue()]
        result = aggregator.aggregate(issues)
        assert hasattr(result, "issues")
        assert hasattr(result, "stats")

    def test_result_is_frozen(self, aggregator):
        result = aggregator.aggregate([])
        with pytest.raises(AttributeError):
            result.stats = {}
