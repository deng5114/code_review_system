from unittest.mock import MagicMock, patch

import pytest

from apps.ai.services.llm_adapter import LLMConfig, LLMResult
from apps.ai.services.response_parser import ParsedIssue, ParsedReviewResponse
from apps.reviews.services.review_engine import ReviewEngine


def _make_project_files():
    return [
        {"path": "app.py", "language": "python", "line_count": 20, "content": "def hello(): pass\n"},
        {"path": "utils.py", "language": "python", "line_count": 10, "content": "x = 1\n"},
    ]


def _make_llm_response():
    return ParsedReviewResponse(
        summary="Found 1 issue.",
        issues=[
            ParsedIssue(
                file_path="app.py", start_line=1, end_line=1,
                severity="high", dimension="security",
                title="SQL Injection", description="Input not sanitized",
                suggestion="Use parameterized queries",
                code_snippet=None, fix_snippet=None, confidence=0.9,
            ),
        ],
    )


def _make_llm_config():
    return LLMConfig(
        provider="openai",
        model_name="gpt-4o",
        api_key="sk-test",
        base_url="",
        extra_settings={},
    )


@pytest.fixture
def mock_engine():
    engine = ReviewEngine()
    return engine


class TestReviewEngineFullPipeline:
    @patch("apps.reviews.services.review_engine.LLMCallManager")
    @patch("apps.reviews.services.review_engine.ResponseParser")
    @patch("apps.reviews.services.review_engine.PromptEngine")
    def test_full_pipeline_small_project(
        self, MockPromptEngine, MockResponseParser, MockLLMCallManager,
    ):
        engine = ReviewEngine()

        prompt_engine = MockPromptEngine.return_value
        prompt_engine.build_review_prompt.return_value = {
            "system_prompt": "system",
            "user_prompt": "user",
        }

        llm_manager = MockLLMCallManager.return_value
        llm_manager.chat_completion.return_value = LLMResult(content="response text", total_tokens=100)
        llm_manager.fallback_logs = []

        response_parser = MockResponseParser.return_value
        response_parser.parse.return_value = _make_llm_response()

        result = engine.run_review(
            project_type="python",
            primary_language="Python",
            frameworks=["django"],
            files=_make_project_files(),
            ai_config=_make_llm_config(),
            custom_instructions="",
        )

        assert result["status"] == "completed"
        assert result["summary"] == "Found 1 issue."
        assert len(result["issues"]) == 1
        assert result["issues"][0]["file_path"] == "app.py"
        assert result["stats"]["total"] == 1
        assert result["stats"]["high_count"] == 1

    @patch("apps.reviews.services.review_engine.LLMCallManager")
    @patch("apps.reviews.services.review_engine.ResponseParser")
    @patch("apps.reviews.services.review_engine.PromptEngine")
    def test_llm_failure_returns_failed(
        self, MockPromptEngine, MockResponseParser, MockLLMCallManager,
    ):
        from apps.ai.services.llm_adapter import LLMCallError

        engine = ReviewEngine()
        prompt_engine = MockPromptEngine.return_value
        prompt_engine.build_review_prompt.return_value = {
            "system_prompt": "s", "user_prompt": "u",
        }

        llm_manager = MockLLMCallManager.return_value
        llm_manager.chat_completion.side_effect = LLMCallError("API timeout")

        result = engine.run_review(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=_make_project_files(),
            ai_config=_make_llm_config(),
        )

        assert result["status"] == "failed"
        assert "API timeout" in result["error_message"]

    @patch("apps.reviews.services.review_engine.LLMCallManager")
    @patch("apps.reviews.services.review_engine.ResponseParser")
    @patch("apps.reviews.services.review_engine.PromptEngine")
    def test_multi_chunk_review(
        self, MockPromptEngine, MockResponseParser, MockLLMCallManager,
    ):
        engine = ReviewEngine(context_window=100)

        prompt_engine = MockPromptEngine.return_value
        prompt_engine.build_review_prompt.return_value = {
            "system_prompt": "s", "user_prompt": "u",
        }

        llm_manager = MockLLMCallManager.return_value
        llm_manager.chat_completion.return_value = LLMResult(content="response", total_tokens=50)
        llm_manager.fallback_logs = []

        response_parser = MockResponseParser.return_value
        response_parser.parse.return_value = ParsedReviewResponse(
            summary="OK", issues=[]
        )

        files = [
            {"path": f"f{i}.py", "language": "python", "line_count": 30, "content": "x=1\n" * 30}
            for i in range(10)
        ]

        result = engine.run_review(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=files,
            ai_config=_make_llm_config(),
        )

        assert result["status"] == "completed"
        assert llm_manager.chat_completion.call_count > 1


class TestReviewEngineProgress:
    @patch("apps.reviews.services.review_engine.LLMCallManager")
    @patch("apps.reviews.services.review_engine.ResponseParser")
    @patch("apps.reviews.services.review_engine.PromptEngine")
    def test_progress_callback_called(
        self, MockPromptEngine, MockResponseParser, MockLLMCallManager,
    ):
        engine = ReviewEngine()
        prompt_engine = MockPromptEngine.return_value
        prompt_engine.build_review_prompt.return_value = {"system_prompt": "s", "user_prompt": "u"}

        llm_manager = MockLLMCallManager.return_value
        llm_manager.chat_completion.return_value = LLMResult(content="ok", total_tokens=10)
        llm_manager.fallback_logs = []

        response_parser = MockResponseParser.return_value
        response_parser.parse.return_value = ParsedReviewResponse(summary="OK", issues=[])

        progress_calls = []
        def on_progress(pct, msg):
            progress_calls.append((pct, msg))

        engine.run_review(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=_make_project_files(),
            ai_config=_make_llm_config(),
            progress_callback=on_progress,
        )

        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100
