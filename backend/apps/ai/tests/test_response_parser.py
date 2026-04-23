import json

from apps.ai.services.response_parser import (
    ParsedIssue,
    ParsedReviewResponse,
    ResponseParser,
)


class TestParsedIssue:
    def test_create_parsed_issue(self):
        issue = ParsedIssue(
            file_path="src/main.py",
            start_line=10,
            end_line=15,
            severity="high",
            dimension="security",
            title="SQL Injection",
            description="User input used directly in query",
            suggestion="Use parameterized queries",
            confidence=0.9,
        )
        assert issue.file_path == "src/main.py"
        assert issue.severity == "high"
        assert issue.confidence == 0.9


class TestParseValidJSON:
    """标准 JSON 响应解析"""

    def test_parse_clean_json(self):
        parser = ResponseParser()
        response = json.dumps({
            "summary": "Found 2 issues",
            "issues": [
                {
                    "file_path": "main.py",
                    "start_line": 1,
                    "end_line": 5,
                    "severity": "high",
                    "dimension": "security",
                    "title": "Hardcoded secret",
                    "description": "API key found in source",
                    "suggestion": "Use environment variable",
                    "code_snippet": "API_KEY = 'abc123'",
                    "fix_snippet": "API_KEY = os.environ['API_KEY']",
                    "confidence": 0.95,
                },
            ],
        })
        result = parser.parse(response)
        assert isinstance(result, ParsedReviewResponse)
        assert result.summary == "Found 2 issues"
        assert len(result.issues) == 1
        assert result.issues[0].severity == "high"

    def test_parse_multiple_issues(self):
        parser = ResponseParser()
        response = json.dumps({
            "summary": "3 issues found",
            "issues": [
                {"file_path": "a.py", "start_line": 1, "end_line": 1, "severity": "critical", "dimension": "security", "title": "T1", "description": "D1", "suggestion": "S1", "confidence": 0.9},
                {"file_path": "b.py", "start_line": 2, "end_line": 3, "severity": "medium", "dimension": "performance", "title": "T2", "description": "D2", "suggestion": "S2", "confidence": 0.7},
                {"file_path": "c.py", "start_line": 5, "end_line": 10, "severity": "low", "dimension": "best_practices", "title": "T3", "description": "D3", "suggestion": "S3", "confidence": 0.5},
            ],
        })
        result = parser.parse(response)
        assert len(result.issues) == 3


class TestParseFromMarkdown:
    """从 markdown 代码块提取 JSON"""

    def test_parse_json_in_code_block(self):
        parser = ResponseParser()
        response = 'Here is the review:\n```json\n{"summary": "OK", "issues": []}\n```'
        result = parser.parse(response)
        assert result.summary == "OK"

    def test_parse_json_in_plain_code_block(self):
        parser = ResponseParser()
        response = '```\n{"summary": "Test", "issues": []}\n```'
        result = parser.parse(response)
        assert result.summary == "Test"

    def test_parse_json_with_surrounding_text(self):
        parser = ResponseParser()
        response = 'I reviewed the code. Here are the results:\n{"summary": "Good", "issues": []}\nHope this helps!'
        result = parser.parse(response)
        assert result.summary == "Good"


class TestFixCommonErrors:
    """修复常见 AI 输出格式错误"""

    def test_fix_trailing_comma(self):
        parser = ResponseParser()
        response = '{"summary": "Test", "issues": [{"severity": "high",},]}'
        result = parser.parse(response)
        assert result.summary == "Test"

    def test_fix_single_quotes(self):
        parser = ResponseParser()
        response = "{'summary': 'Test', 'issues': []}"
        result = parser.parse(response)
        assert result.summary == "Test"

    def test_fix_comments_in_json(self):
        parser = ResponseParser()
        response = '{\n  "summary": "Test", // this is a comment\n  "issues": []\n}'
        result = parser.parse(response)
        assert result.summary == "Test"

    def test_fix_unquoted_keys(self):
        parser = ResponseParser()
        response = '{summary: "Test", issues: []}'
        result = parser.parse(response)
        assert result.summary == "Test"


class TestValidation:
    """字段验证"""

    def test_invalid_severity_normalized(self):
        parser = ResponseParser()
        response = json.dumps({
            "summary": "Test",
            "issues": [{
                "file_path": "a.py", "start_line": 1, "end_line": 1,
                "severity": "CRITICAL", "dimension": "security",
                "title": "T", "description": "D", "suggestion": "S", "confidence": 0.9,
            }],
        })
        result = parser.parse(response)
        assert result.issues[0].severity == "critical"

    def test_missing_optional_fields_get_defaults(self):
        parser = ResponseParser()
        response = json.dumps({
            "summary": "Test",
            "issues": [{
                "file_path": "a.py", "start_line": 1, "end_line": 1,
                "severity": "high", "dimension": "security",
                "title": "T", "description": "D", "suggestion": "S", "confidence": 0.9,
            }],
        })
        result = parser.parse(response)
        assert result.issues[0].code_snippet == ""
        assert result.issues[0].fix_snippet == ""

    def test_confidence_clamped_to_range(self):
        parser = ResponseParser()
        response = json.dumps({
            "summary": "Test",
            "issues": [{
                "file_path": "a.py", "start_line": 1, "end_line": 1,
                "severity": "high", "dimension": "security",
                "title": "T", "description": "D", "suggestion": "S",
                "confidence": 1.5,
            }],
        })
        result = parser.parse(response)
        assert result.issues[0].confidence == 1.0

    def test_invalid_issue_skipped(self):
        parser = ResponseParser()
        response = json.dumps({
            "summary": "Test",
            "issues": [
                {"severity": "high"},  # missing required fields
                {"file_path": "a.py", "start_line": 1, "end_line": 1, "severity": "medium", "dimension": "security", "title": "T", "description": "D", "suggestion": "S", "confidence": 0.8},
            ],
        })
        result = parser.parse(response)
        assert len(result.issues) == 1
        assert result.issues[0].severity == "medium"


class TestParseFailure:
    """完全无法解析的情况"""

    def test_completely_invalid_returns_empty(self):
        parser = ResponseParser()
        result = parser.parse("This is not JSON at all, just plain text.")
        assert isinstance(result, ParsedReviewResponse)
        assert result.summary == ""
        assert len(result.issues) == 0

    def test_empty_string(self):
        parser = ResponseParser()
        result = parser.parse("")
        assert len(result.issues) == 0

    def test_none_input(self):
        parser = ResponseParser()
        result = parser.parse(None)
        assert len(result.issues) == 0
