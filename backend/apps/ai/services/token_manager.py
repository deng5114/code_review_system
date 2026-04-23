import tiktoken

# 模型上下文窗口大小映射
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "o1": 200_000,
    "o1-mini": 128_000,
    "o3-mini": 200_000,
    # Anthropic
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-haiku-20240307": 200_000,
    # Google
    "gemini/gemini-2.0-flash": 1_048_576,
    "gemini/gemini-2.5-pro": 1_048_576,
    "gemini/gemini-1.5-pro": 2_097_152,
    # DeepSeek
    "deepseek/deepseek-chat": 128_000,
    "deepseek/deepseek-coder": 128_000,
    # Ollama (common models)
    "ollama/llama3": 8_192,
    "ollama/codellama": 16_384,
    "ollama/qwen2.5-coder": 128_000,
    # OpenRouter
    "openrouter/auto": 128_000,
}

DEFAULT_CONTEXT_WINDOW = 128_000
ESTIMATED_CHARS_PER_TOKEN = 4  # 平均 4 个字符约 1 个 token


class TokenManager:
    """Token 计算和上下文窗口管理"""

    _encoders: dict[str, tiktoken.Encoding] = {}

    def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        if not text:
            return 0

        encoding = self._get_encoding(model)
        try:
            return len(encoding.encode(text))
        except Exception:
            return len(text) // ESTIMATED_CHARS_PER_TOKEN

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        if not text:
            return ""

        encoding = self._get_encoding("gpt-4o")
        try:
            tokens = encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text
            return encoding.decode(tokens[:max_tokens])
        except Exception:
            estimated_chars = max_tokens * ESTIMATED_CHARS_PER_TOKEN
            return text[:estimated_chars]

    def get_model_context_window(self, model: str) -> int:
        if model in MODEL_CONTEXT_WINDOWS:
            return MODEL_CONTEXT_WINDOWS[model]

        # 部分匹配：gpt-4o-2024-08-06 匹配 gpt-4o
        for key, window in MODEL_CONTEXT_WINDOWS.items():
            if model.startswith(key):
                return window

        return DEFAULT_CONTEXT_WINDOW

    def calculate_available_budget(
        self,
        model: str,
        system_prompt: str,
        user_content: str,
        output_reserve: int = 2000,
    ) -> int:
        total_window = self.get_model_context_window(model)
        system_tokens = self.count_tokens(system_prompt, model)
        user_tokens = self.count_tokens(user_content, model)
        used = system_tokens + user_tokens + output_reserve
        return max(0, total_window - used)

    def _get_encoding(self, model: str) -> tiktoken.Encoding:
        if model not in self._encoders:
            try:
                self._encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                self._encoders[model] = tiktoken.get_encoding("cl100k_base")
        return self._encoders[model]
