import logging
import time
from dataclasses import dataclass

from litellm import completion as litellm_completion

logger = logging.getLogger(__name__)

ALLOWED_EXTRA_KEYS = frozenset({
    "temperature", "max_tokens", "top_p",
    "frequency_penalty", "presence_penalty",
})


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model_name: str
    api_key: str
    base_url: str
    extra_settings: dict

    @classmethod
    def from_ai_config(cls, ai_config) -> "LLMConfig":
        return cls(
            provider=ai_config.provider,
            model_name=ai_config.model_name,
            api_key=ai_config.api_key,
            base_url=ai_config.base_url,
            extra_settings=dict(ai_config.extra_settings),
        )


@dataclass(frozen=True)
class LLMResult:
    content: str
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMCallError(Exception):
    pass


class LLMAdapter:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def chat_completion(
        self,
        config: LLMConfig,
        messages: list[dict],
    ) -> LLMResult:
        params = self._build_litellm_params(config, messages)
        return self._retry_with_backoff(params)

    def _build_litellm_params(
        self, config: LLMConfig, messages: list[dict]
    ) -> dict:
        model = f"{config.provider}/{config.model_name}"
        params: dict = {
            "model": model,
            "messages": messages,
        }
        if config.api_key:
            params["api_key"] = config.api_key
        if config.base_url:
            params["api_base"] = config.base_url
        params.update({
            k: v for k, v in config.extra_settings.items()
            if k in ALLOWED_EXTRA_KEYS
        })
        return params

    def _retry_with_backoff(self, params: dict) -> LLMResult:
        max_attempts = max(self._max_retries, 1)
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = litellm_completion(**params)
                return self._extract_result(response)
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 调用失败 (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    str(e),
                )
                if attempt < max_attempts - 1:
                    time.sleep(self._retry_delay * (2 ** attempt))
        raise LLMCallError(
            f"LLM 调用失败，已重试 {max_attempts} 次: {last_error}"
        ) from last_error

    def _extract_result(self, response) -> LLMResult:
        content = response.choices[0].message.content
        usage = response.usage
        if usage is None:
            return LLMResult(content=content)
        return LLMResult(
            content=content,
            total_tokens=usage.total_tokens or 0,
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
        )
