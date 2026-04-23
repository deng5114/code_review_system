import pytest

from apps.ai.services.prompt_engine import PromptEngine


@pytest.fixture
def engine():
    return PromptEngine()


class TestPromptEngine:
    def test_build_review_prompt_contains_project_type(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=["django"],
            files=[{"path": "main.py", "language": "python", "line_count": 10, "content": "print('hi')"}],
        )
        assert "python" in result["user_prompt"]
        assert "Python" in result["user_prompt"]

    def test_build_prompt_with_frameworks(self, engine):
        result = engine.build_review_prompt(
            project_type="nodejs",
            primary_language="TypeScript",
            frameworks=["react", "nextjs"],
            files=[{"path": "app.tsx", "language": "typescript", "line_count": 20, "content": "export default App()"}],
        )
        assert "react" in result["user_prompt"]
        assert "nextjs" in result["user_prompt"]

    def test_build_prompt_without_frameworks(self, engine):
        result = engine.build_review_prompt(
            project_type="go",
            primary_language="Go",
            frameworks=[],
            files=[{"path": "main.go", "language": "go", "line_count": 5, "content": "package main"}],
        )
        assert "Go" in result["user_prompt"]

    def test_build_prompt_with_custom_instructions(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
            custom_instructions="重点关注安全问题",
        )
        assert "重点关注安全问题" in result["user_prompt"]

    def test_build_prompt_without_custom_instructions(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
        )
        assert "自定义审查要求" not in result["user_prompt"]

    def test_build_prompt_contains_file_content(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[
                {"path": "src/app.py", "language": "python", "line_count": 3, "content": "def hello():\n    return 'hi'\n"},
            ],
        )
        assert "src/app.py" in result["user_prompt"]
        assert "def hello():" in result["user_prompt"]

    def test_build_prompt_multiple_files(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[
                {"path": "a.py", "language": "python", "line_count": 1, "content": "x=1"},
                {"path": "b.py", "language": "python", "line_count": 2, "content": "y=2\nz=3"},
            ],
        )
        assert "a.py" in result["user_prompt"]
        assert "b.py" in result["user_prompt"]

    def test_system_prompt_is_consistent(self, engine):
        result1 = engine.build_review_prompt(
            project_type="python", primary_language="Python", frameworks=[], files=[],
        )
        result2 = engine.build_review_prompt(
            project_type="go", primary_language="Go", frameworks=[], files=[],
        )
        assert result1["system_prompt"] == result2["system_prompt"]

    def test_output_format_instruction_included(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "main.py", "language": "python", "line_count": 1, "content": "x=1"}],
        )
        assert "JSON" in result["user_prompt"]
        assert "severity" in result["user_prompt"]
        assert "dimension" in result["user_prompt"]

    def test_total_files_included(self, engine):
        result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=[{"path": "a.py", "language": "python", "line_count": 1, "content": "x=1"}],
            total_files=42,
        )
        assert "42" in result["user_prompt"]
