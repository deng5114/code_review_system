from apps.ai.services.token_manager import (
    MODEL_CONTEXT_WINDOWS,
    ESTIMATED_CHARS_PER_TOKEN,
    TokenManager,
)


class TestConstants:
    def test_model_context_windows_has_major_models(self):
        assert "gpt-4o" in MODEL_CONTEXT_WINDOWS
        assert "gpt-4o-mini" in MODEL_CONTEXT_WINDOWS
        assert "claude-sonnet-4-20250514" in MODEL_CONTEXT_WINDOWS
        assert "gemini/gemini-2.0-flash" in MODEL_CONTEXT_WINDOWS

    def test_all_context_windows_positive(self):
        for model, window in MODEL_CONTEXT_WINDOWS.items():
            assert window > 0, f"{model} has non-positive context window: {window}"

    def test_estimated_chars_per_token(self):
        assert ESTIMATED_CHARS_PER_TOKEN > 0


class TestCountTokens:
    def test_count_english_text(self):
        tm = TokenManager()
        text = "Hello, this is a test of the token counter."
        tokens = tm.count_tokens(text)
        assert tokens > 0
        assert tokens < 50  # short text

    def test_count_python_code(self):
        tm = TokenManager()
        code = "def hello(name: str) -> str:\n    return f'Hello {name}'\n"
        tokens = tm.count_tokens(code)
        assert tokens > 0

    def test_count_empty_text(self):
        tm = TokenManager()
        assert tm.count_tokens("") == 0

    def test_count_multiline_text(self):
        tm = TokenManager()
        text = "line 1\nline 2\nline 3\n" * 100
        tokens = tm.count_tokens(text)
        assert tokens > 100

    def test_count_with_model_parameter(self):
        tm = TokenManager()
        text = "Hello world"
        tokens = tm.count_tokens(text, model="gpt-4o")
        assert tokens > 0


class TestTruncateToTokens:
    def test_truncate_long_text(self):
        tm = TokenManager()
        long_text = "word " * 5000
        truncated = tm.truncate_to_tokens(long_text, max_tokens=100)
        assert tm.count_tokens(truncated) <= 110  # small margin

    def test_truncate_short_text_unchanged(self):
        tm = TokenManager()
        short_text = "Hello world"
        result = tm.truncate_to_tokens(short_text, max_tokens=100)
        assert result == short_text

    def test_truncate_empty_text(self):
        tm = TokenManager()
        assert tm.truncate_to_tokens("", max_tokens=100) == ""


class TestGetModelContextWindow:
    def test_known_model(self):
        tm = TokenManager()
        window = tm.get_model_context_window("gpt-4o")
        assert window == MODEL_CONTEXT_WINDOWS["gpt-4o"]

    def test_unknown_model_returns_default(self):
        tm = TokenManager()
        window = tm.get_model_context_window("unknown-model-xyz")
        assert window > 0  # default fallback

    def test_partial_model_name_match(self):
        tm = TokenManager()
        window = tm.get_model_context_window("gpt-4o-2024-08-06")
        assert window > 0  # should match gpt-4o pattern


class TestTokenBudget:
    def test_calculate_available_tokens(self):
        tm = TokenManager()
        system_prompt = "You are a code reviewer."
        user_prompt = "Review this code: def add(a, b): return a + b"
        available = tm.calculate_available_budget(
            model="gpt-4o",
            system_prompt=system_prompt,
            user_content=user_prompt,
            output_reserve=1000,
        )
        assert available > 0
        total_window = tm.get_model_context_window("gpt-4o")
        assert available < total_window

    def test_budget_never_negative(self):
        tm = TokenManager()
        # Use a very long prompt
        long_text = "x" * 1_000_000
        available = tm.calculate_available_budget(
            model="gpt-4o",
            system_prompt=long_text,
            user_content="short",
            output_reserve=1000,
        )
        assert available >= 0
