from unittest.mock import MagicMock, patch

import pytest

from apps.ai.services.llm_adapter import LLMAdapter, LLMCallError, LLMConfig


@pytest.fixture
def openai_config():
    return LLMConfig(
        provider="openai",
        model_name="gpt-4o",
        api_key="sk-test-key-12345678",
        base_url="",
        extra_settings={},
    )


@pytest.fixture
def anthropic_config():
    return LLMConfig(
        provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
        base_url="",
        extra_settings={},
    )


@pytest.fixture
def ollama_config():
    return LLMConfig(
        provider="ollama",
        model_name="llama3",
        api_key="",
        base_url="http://localhost:11434",
        extra_settings={},
    )


@pytest.fixture
def deepseek_config():
    return LLMConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        api_key="sk-deepseek-key",
        base_url="",
        extra_settings={},
    )


@pytest.fixture
def adapter():
    return LLMAdapter(max_retries=3, retry_delay=0.01)


class TestLLMConfig:
    def test_create_config(self, openai_config):
        assert openai_config.provider == "openai"
        assert openai_config.model_name == "gpt-4o"
        assert openai_config.api_key == "sk-test-key-12345678"


class TestBuildLiteLLMParams:
    def test_openai_params(self, adapter, openai_config):
        params = adapter._build_litellm_params(
            openai_config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["model"] == "openai/gpt-4o"
        assert params["api_key"] == "sk-test-key-12345678"
        assert params["messages"] == [{"role": "user", "content": "hi"}]

    def test_anthropic_params(self, adapter, anthropic_config):
        params = adapter._build_litellm_params(
            anthropic_config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["model"] == "anthropic/claude-sonnet-4-20250514"
        assert params["api_key"] == "sk-ant-test-key"

    def test_ollama_params(self, adapter, ollama_config):
        params = adapter._build_litellm_params(
            ollama_config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["model"] == "ollama/llama3"
        assert params["api_base"] == "http://localhost:11434"

    def test_deepseek_params(self, adapter, deepseek_config):
        params = adapter._build_litellm_params(
            deepseek_config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["model"] == "deepseek/deepseek-chat"

    def test_custom_base_url(self, adapter):
        config = LLMConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-test",
            base_url="https://custom.api.com/v1",
            extra_settings={},
        )
        params = adapter._build_litellm_params(
            config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["api_base"] == "https://custom.api.com/v1"

    def test_extra_settings_passed(self, adapter, openai_config):
        openai_config = LLMConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-test",
            base_url="",
            extra_settings={"temperature": 0.7, "max_tokens": 4096},
        )
        params = adapter._build_litellm_params(
            openai_config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 4096

    def test_extra_settings_filters_dangerous_keys(self, adapter):
        config = LLMConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-safe-key",
            base_url="",
            extra_settings={
                "temperature": 0.5,
                "model": "malicious-model",
                "api_key": "stolen-key",
                "api_base": "http://evil.com",
            },
        )
        params = adapter._build_litellm_params(
            config, messages=[{"role": "user", "content": "hi"}]
        )
        assert params["temperature"] == 0.5
        assert params["model"] == "openai/gpt-4o"
        assert params["api_key"] == "sk-safe-key"
        assert "api_base" not in params


class TestChatCompletion:
    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_successful_call(self, mock_completion, adapter, openai_config):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"summary": "ok", "issues": []}'
        mock_response.usage.total_tokens = 150
        mock_completion.return_value = mock_response

        result = adapter.chat_completion(
            config=openai_config,
            messages=[{"role": "user", "content": "review this"}],
        )
        assert result.content == '{"summary": "ok", "issues": []}'
        assert result.total_tokens == 150
        mock_completion.assert_called_once()

    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_messages_passed_correctly(self, mock_completion, adapter, openai_config):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.total_tokens = 50
        mock_completion.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a reviewer"},
            {"role": "user", "content": "Review this code"},
        ]
        adapter.chat_completion(config=openai_config, messages=messages)

        call_args = mock_completion.call_args[1]
        assert call_args["messages"] == messages


class TestRetryLogic:
    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_retry_on_failure_then_success(self, mock_completion, adapter, openai_config):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "success"
        mock_response.usage.total_tokens = 10
        mock_completion.side_effect = [Exception("API Error"), mock_response]

        result = adapter.chat_completion(
            config=openai_config,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result.content == "success"
        assert mock_completion.call_count == 2

    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_retry_exhausted_raises_error(self, mock_completion, adapter, openai_config):
        mock_completion.side_effect = Exception("Persistent error")

        with pytest.raises(LLMCallError, match="LLM 调用失败"):
            adapter.chat_completion(
                config=openai_config,
                messages=[{"role": "user", "content": "hi"}],
            )
        assert mock_completion.call_count == 3

    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_no_retry_on_zero_max(self, mock_completion):
        adapter_no_retry = LLMAdapter(max_retries=0)
        mock_completion.side_effect = Exception("Fail fast")

        with pytest.raises(LLMCallError):
            adapter_no_retry.chat_completion(
                config=LLMConfig(
                    provider="openai",
                    model_name="gpt-4o",
                    api_key="sk-test",
                    base_url="",
                    extra_settings={},
                ),
                messages=[{"role": "user", "content": "hi"}],
            )
        assert mock_completion.call_count == 1


class TestLLMResult:
    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_result_has_content_and_tokens(self, mock_completion, adapter, openai_config):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "review result"
        mock_response.usage.total_tokens = 200
        mock_response.usage.prompt_tokens = 150
        mock_response.usage.completion_tokens = 50
        mock_completion.return_value = mock_response

        result = adapter.chat_completion(
            config=openai_config,
            messages=[{"role": "user", "content": "review"}],
        )
        assert result.content == "review result"
        assert result.total_tokens == 200
        assert result.prompt_tokens == 150
        assert result.completion_tokens == 50

    @patch("apps.ai.services.llm_adapter.litellm_completion")
    def test_result_with_none_usage(self, mock_completion, adapter, openai_config):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "result"
        mock_response.usage = None
        mock_completion.return_value = mock_response

        result = adapter.chat_completion(
            config=openai_config,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result.content == "result"
        assert result.total_tokens == 0
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0


class TestFromAIConfig:
    def test_create_config_from_model(self):
        mock_aiconfig = MagicMock()
        mock_aiconfig.provider = "openai"
        mock_aiconfig.model_name = "gpt-4o"
        mock_aiconfig.api_key = "sk-real-key"
        mock_aiconfig.base_url = ""
        mock_aiconfig.extra_settings = {"temperature": 0.5}

        config = LLMConfig.from_ai_config(mock_aiconfig)
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o"
        assert config.api_key == "sk-real-key"
        assert config.extra_settings == {"temperature": 0.5}
