import pytest

from apps.ai.services.prompt_engine import PromptEngine


@pytest.fixture
def engine():
    return PromptEngine()


SUPPORTED_LANGUAGES = ["python", "typescript", "go", "java", "rust"]

LANGUAGE_KEYWORDS = {
    "python": ["PEP 8", "f-string", "Django", "Flask"],
    "typescript": ["XSS", "strict", "React", "async/await"],
    "go": ["goroutine", "context.Context", "Gin", "defer"],
    "java": ["PreparedStatement", "Spring Boot", "Optional", "try-with-resources"],
    "rust": ["unsafe", "Result<T, E>", "Tokio", "clone()"],
}


class TestLanguageSpecificGuidance:
    def test_supported_language_loads_guidance(self, engine):
        for lang in SUPPORTED_LANGUAGES:
            result = engine.build_review_prompt(
                project_type="unknown",
                primary_language=lang,
                frameworks=[],
                files=[{"path": f"main.{lang}", "language": lang, "line_count": 1, "content": "x=1"}],
            )
            assert result["user_prompt"], f"{lang} prompt should not be empty"
            assert "语言专项审查指南" in result["user_prompt"], (
                f"{lang} should include language guidance section"
            )

    def test_guidance_contains_language_keywords(self, engine):
        for lang, keywords in LANGUAGE_KEYWORDS.items():
            result = engine.build_review_prompt(
                project_type="unknown",
                primary_language=lang,
                frameworks=[],
                files=[{"path": f"main.{lang}", "language": lang, "line_count": 1, "content": "x=1"}],
            )
            matched = [kw for kw in keywords if kw in result["user_prompt"]]
            assert matched, (
                f"{lang} guidance should contain at least one of {keywords}"
            )

    def test_unsupported_language_graceful_degradation(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="cobol",
            frameworks=[],
            files=[{"path": "main.cob", "language": "cobol", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" not in result["user_prompt"]
        assert "cobol" in result["user_prompt"]

    def test_case_insensitive_language_matching(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" in result["user_prompt"]
        assert "PEP 8" in result["user_prompt"]

    def test_language_alias_javascript_to_typescript(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="javascript",
            frameworks=[],
            files=[{"path": "main.js", "language": "javascript", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" in result["user_prompt"]
        assert "XSS" in result["user_prompt"]

    def test_language_alias_py_to_python(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="py",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" in result["user_prompt"]
        assert "PEP 8" in result["user_prompt"]

    def test_language_alias_golang_to_go(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="golang",
            frameworks=[],
            files=[{"path": "main.go", "language": "go", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" in result["user_prompt"]
        assert "goroutine" in result["user_prompt"]

    def test_guidance_appears_before_code(self, engine):
        code_content = "def hello(): return 'world'"
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": code_content}],
        )
        guidance_pos = result["user_prompt"].find("语言专项审查指南")
        code_pos = result["user_prompt"].find(code_content)
        assert guidance_pos > 0, "Guidance should be present"
        assert code_pos > 0, "Code should be present"
        assert guidance_pos < code_pos, "Guidance should appear before code"

    def test_guidance_with_custom_instructions(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
            custom_instructions="重点关注安全问题",
        )
        assert "语言专项审查指南" in result["user_prompt"]
        assert "重点关注安全问题" in result["user_prompt"]

    def test_path_traversal_rejected(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="../../etc/passwd",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" not in result["user_prompt"]

    def test_path_traversal_with_slash_rejected(self, engine):
        result = engine.build_review_prompt(
            project_type="unknown",
            primary_language="../system_base",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
        )
        assert "语言专项审查指南" not in result["user_prompt"]
