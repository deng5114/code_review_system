from unittest.mock import MagicMock, patch

import pytest

from apps.ai.services.llm_adapter import LLMCallError, LLMConfig, LLMResult
from apps.ai.services.llm_call_manager import LLMCallManager


def _make_config(model_name: str, provider: str = "openai") -> LLMConfig:
    return LLMConfig(
        provider=provider,
        model_name=model_name,
        api_key="test-key",
        base_url="",
        extra_settings={},
    )


def _make_result(content: str) -> LLMResult:
    return LLMResult(content=content, total_tokens=10)


class TestLLMCallManager:
    def test_primary_success_no_fallback(self):
        adapter = MagicMock()
        adapter.chat_completion.return_value = _make_result("ok")

        manager = LLMCallManager(adapter=adapter)
        primary = _make_config("gpt-4o")
        messages = [{"role": "user", "content": "hi"}]

        result = manager.chat_completion(
            primary_config=primary,
            fallback_configs=[],
            messages=messages,
        )

        assert result.content == "ok"
        adapter.chat_completion.assert_called_once_with(
            config=primary, messages=messages,
        )
        assert manager.fallback_logs == []

    def test_fallback_on_primary_failure(self):
        adapter = MagicMock()
        adapter.chat_completion.side_effect = [
            LLMCallError("primary failed"),
            _make_result("fallback ok"),
        ]

        manager = LLMCallManager(adapter=adapter)
        primary = _make_config("gpt-4o")
        fallback = _make_config("gpt-3.5-turbo")
        messages = [{"role": "user", "content": "hi"}]

        result = manager.chat_completion(
            primary_config=primary,
            fallback_configs=[fallback],
            messages=messages,
        )

        assert result.content == "fallback ok"
        assert adapter.chat_completion.call_count == 2
        assert len(manager.fallback_logs) == 1
        assert manager.fallback_logs[0].original_config == "gpt-4o"
        assert manager.fallback_logs[0].fallback_config == "gpt-3.5-turbo"

    def test_all_configs_fail_raises_error(self):
        adapter = MagicMock()
        adapter.chat_completion.side_effect = LLMCallError("fail")

        manager = LLMCallManager(adapter=adapter)
        primary = _make_config("gpt-4o")
        fallbacks = [_make_config("gpt-3.5-turbo"), _make_config("claude-3")]

        with pytest.raises(LLMCallError, match="主配置和 2 个备用配置均失败"):
            manager.chat_completion(
                primary_config=primary,
                fallback_configs=fallbacks,
                messages=[],
            )

        assert len(manager.fallback_logs) == 2

    def test_max_fallbacks_limits_attempts(self):
        adapter = MagicMock()
        adapter.chat_completion.side_effect = LLMCallError("fail")

        manager = LLMCallManager(adapter=adapter, max_fallbacks=1)
        primary = _make_config("gpt-4o")
        fallbacks = [_make_config("model-a"), _make_config("model-b")]

        with pytest.raises(LLMCallError):
            manager.chat_completion(
                primary_config=primary,
                fallback_configs=fallbacks,
                messages=[],
            )

        assert len(manager.fallback_logs) == 1
        assert adapter.chat_completion.call_count == 2  # primary + 1 fallback

    def test_no_fallback_configs_raises_original_error(self):
        adapter = MagicMock()
        adapter.chat_completion.side_effect = LLMCallError("primary error")

        manager = LLMCallManager(adapter=adapter)
        primary = _make_config("gpt-4o")

        with pytest.raises(LLMCallError, match="primary error"):
            manager.chat_completion(
                primary_config=primary,
                fallback_configs=[],
                messages=[],
            )

    def test_fallback_logs_cleared_per_call(self):
        adapter = MagicMock()
        adapter.chat_completion.side_effect = [
            LLMCallError("fail"),
            _make_result("ok"),
            _make_result("direct ok"),
        ]

        manager = LLMCallManager(adapter=adapter)
        primary = _make_config("gpt-4o")
        fallback = _make_config("gpt-3.5-turbo")

        manager.chat_completion(
            primary_config=primary,
            fallback_configs=[fallback],
            messages=[],
        )
        assert len(manager.fallback_logs) == 1

        manager.chat_completion(
            primary_config=primary,
            fallback_configs=[fallback],
            messages=[],
        )
        assert len(manager.fallback_logs) == 0

    def test_second_fallback_succeeds(self):
        adapter = MagicMock()
        adapter.chat_completion.side_effect = [
            LLMCallError("primary failed"),
            LLMCallError("first fallback failed"),
            _make_result("second fallback ok"),
        ]

        manager = LLMCallManager(adapter=adapter)
        primary = _make_config("gpt-4o")
        fallbacks = [_make_config("gpt-3.5-turbo"), _make_config("claude-3")]

        result = manager.chat_completion(
            primary_config=primary,
            fallback_configs=fallbacks,
            messages=[],
        )

        assert result.content == "second fallback ok"
        assert len(manager.fallback_logs) == 2
        assert manager.fallback_logs[0].fallback_config == "gpt-3.5-turbo"
        assert manager.fallback_logs[1].fallback_config == "claude-3"


class TestBuildFallbackChain:
    def test_builds_chain_sorted_by_priority(self):
        configs = []
        for name, priority, fallback in [
            ("low", 1, True),
            ("high", 10, True),
            ("medium", 5, True),
        ]:
            cfg = MagicMock()
            cfg.is_active = True
            cfg.fallback_enabled = fallback
            cfg.priority = priority
            cfg.model_name = name
            cfg.provider = "openai"
            cfg.api_key = "key"
            cfg.base_url = ""
            cfg.extra_settings = {}
            configs.append(cfg)

        chain = LLMCallManager.build_fallback_chain(configs)
        assert len(chain) == 3
        assert chain[0].model_name == "high"
        assert chain[1].model_name == "medium"
        assert chain[2].model_name == "low"

    def test_filters_inactive_configs(self):
        active = MagicMock()
        active.is_active = True
        active.fallback_enabled = True
        active.priority = 1
        active.provider = "openai"
        active.model_name = "active"
        active.api_key = "key"
        active.base_url = ""
        active.extra_settings = {}

        inactive = MagicMock()
        inactive.is_active = False
        inactive.fallback_enabled = True
        inactive.priority = 10

        chain = LLMCallManager.build_fallback_chain([active, inactive])
        assert len(chain) == 1
        assert chain[0].model_name == "active"

    def test_filters_non_fallback_configs(self):
        fallback = MagicMock()
        fallback.is_active = True
        fallback.fallback_enabled = True
        fallback.priority = 1
        fallback.provider = "openai"
        fallback.model_name = "fallback"
        fallback.api_key = "key"
        fallback.base_url = ""
        fallback.extra_settings = {}

        no_fallback = MagicMock()
        no_fallback.is_active = True
        no_fallback.fallback_enabled = False
        no_fallback.priority = 10

        chain = LLMCallManager.build_fallback_chain([fallback, no_fallback])
        assert len(chain) == 1
        assert chain[0].model_name == "fallback"

    def test_empty_input(self):
        chain = LLMCallManager.build_fallback_chain([])
        assert chain == []
