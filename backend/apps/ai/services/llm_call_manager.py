import logging
from dataclasses import dataclass

from apps.ai.services.llm_adapter import LLMAdapter, LLMCallError, LLMConfig, LLMResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FallbackLog:
    original_config: str
    fallback_config: str
    attempt: int
    error: str


class LLMCallManager:
    """LLM 调用管理器：支持主配置失败后按优先级自动降级到备用配置"""

    def __init__(self, adapter: LLMAdapter, max_fallbacks: int = 3) -> None:
        self._adapter = adapter
        self._max_fallbacks = max_fallbacks
        self._fallback_logs: list[FallbackLog] = []

    @property
    def fallback_logs(self) -> list[FallbackLog]:
        return list(self._fallback_logs)

    def chat_completion(
        self,
        primary_config: LLMConfig,
        fallback_configs: list[LLMConfig],
        messages: list[dict],
    ) -> LLMResult:
        self._fallback_logs.clear()
        try:
            result = self._adapter.chat_completion(
                config=primary_config, messages=messages,
            )
            return result
        except LLMCallError as e:
            logger.warning(
                "主配置调用失败 (%s): %s，尝试降级...",
                primary_config.model_name,
                str(e),
            )
            return self._try_fallbacks(
                primary_config=primary_config,
                fallback_configs=fallback_configs,
                messages=messages,
                original_error=e,
            )

    def _try_fallbacks(
        self,
        primary_config: LLMConfig,
        fallback_configs: list[LLMConfig],
        messages: list[dict],
        original_error: LLMCallError,
    ) -> LLMResult:
        eligible = fallback_configs[: self._max_fallbacks]
        if not eligible:
            logger.error("无可用备用配置，降级失败")
            raise original_error

        last_error: Exception = original_error
        for i, config in enumerate(eligible, 1):
            log_entry = FallbackLog(
                original_config=primary_config.model_name,
                fallback_config=config.model_name,
                attempt=i,
                error=str(last_error),
            )
            self._fallback_logs.append(log_entry)
            logger.info(
                "降级尝试 %d/%d: %s → %s",
                i,
                len(eligible),
                primary_config.model_name,
                config.model_name,
            )
            try:
                result = self._adapter.chat_completion(
                    config=config, messages=messages,
                )
                logger.info(
                    "降级成功: 使用 %s 完成调用",
                    config.model_name,
                )
                return result
            except LLMCallError as e:
                last_error = e
                logger.warning(
                    "备用配置 %s 调用失败: %s",
                    config.model_name,
                    str(e),
                )

        logger.error(
            "所有降级配置均失败 (尝试了 %d 个备用)",
            len(eligible),
        )
        raise LLMCallError(
            f"主配置和 {len(eligible)} 个备用配置均失败: {last_error}"
        ) from last_error

    @staticmethod
    def build_fallback_chain(ai_configs: list) -> list[LLMConfig]:
        """从 AIConfig 查询集构建降级链，按优先级降序排列"""
        eligible = [
            cfg for cfg in ai_configs
            if cfg.is_active and cfg.fallback_enabled
        ]
        sorted_configs = sorted(eligible, key=lambda c: c.priority, reverse=True)
        return [LLMConfig.from_ai_config(cfg) for cfg in sorted_configs]
