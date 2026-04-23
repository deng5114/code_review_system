"""集成测试：Prompt 组装 → LLM 调用 → 响应解析 完整流程"""
from unittest.mock import MagicMock, patch

import pytest

from apps.ai.services.llm_adapter import LLMAdapter, LLMConfig
from apps.ai.services.prompt_engine import PromptEngine
from apps.ai.services.response_parser import ResponseParser


@pytest.fixture
def openai_config():
    return LLMConfig(
        provider="openai",
        model_name="gpt-4o",
        api_key="sk-test-integration-key",
        base_url="",
        extra_settings={"temperature": 0.3},
    )


@pytest.fixture
def sample_files():
    return [
        {
            "path": "app.py",
            "language": "python",
            "line_count": 15,
            "content": (
                "from flask import Flask, request\n"
                "app = Flask(__name__)\n"
                "\n"
                "@app.route('/login', methods=['POST'])\n"
                "def login():\n"
                "    username = request.form['username']\n"
                "    password = request.form['password']\n"
                "    query = f\"SELECT * FROM users WHERE username='{username}'\"\n"
                "    # TODO: use parameterized query\n"
                "    user = db.execute(query).fetchone()\n"
                "    if user and user.password == password:\n"
                "        return {'token': create_token(user.id)}\n"
                "    return {'error': 'Invalid credentials'}, 401\n"
            ),
        },
        {
            "path": "utils.py",
            "language": "python",
            "line_count": 5,
            "content": (
                "def process_data(data):\n"
                "    result = {}\n"
                "    for item in data:\n"
                "        result[item['id']] = item\n"
                "    return result\n"
            ),
        },
    ]


MOCK_LLM_RESPONSE = """\
{
  "summary": "发现 SQL 注入漏洞和明文密码比较问题，建议立即修复安全相关代码。",
  "issues": [
    {
      "file_path": "app.py",
      "start_line": 8,
      "end_line": 8,
      "severity": "critical",
      "dimension": "security",
      "title": "SQL 注入漏洞",
      "description": "使用字符串拼接构建 SQL 查询，攻击者可通过 username 字段注入恶意 SQL",
      "suggestion": "使用参数化查询替代字符串拼接",
      "code_snippet": "query = f\\"SELECT * FROM users WHERE username='{username}'\\"",
      "fix_snippet": "query = \\"SELECT * FROM users WHERE username=?\\"",
      "confidence": 0.95
    },
    {
      "file_path": "app.py",
      "start_line": 11,
      "end_line": 11,
      "severity": "critical",
      "dimension": "security",
      "title": "明文密码比较",
      "description": "直接比较明文密码，未使用哈希验证",
      "suggestion": "使用 bcrypt 或 argon2 进行密码哈希比较",
      "confidence": 0.92
    },
    {
      "file_path": "app.py",
      "start_line": 1,
      "end_line": 1,
      "severity": "medium",
      "dimension": "best_practices",
      "title": "使用 Flask 而非 Django",
      "description": "项目未使用 Django 框架",
      "suggestion": "考虑迁移到 Django 以获得更好的安全特性",
      "confidence": 0.4
    }
  ]
}
"""


class TestFullPipeline:
    """完整流程：Prompt 组装 → LLM 调用 → 响应解析"""

    def test_full_pipeline_with_mock(
        self, openai_config, sample_files
    ):
        # 1. 组装 Prompt
        engine = PromptEngine()
        prompt_result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=["flask"],
            files=sample_files,
            custom_instructions="重点关注安全问题",
            total_files=2,
        )
        assert "system_prompt" in prompt_result
        assert "user_prompt" in prompt_result
        assert "flask" in prompt_result["user_prompt"]
        assert "app.py" in prompt_result["user_prompt"]
        assert "重点关注安全问题" in prompt_result["user_prompt"]

        # 2. Mock LLM 调用
        adapter = LLMAdapter(max_retries=1, retry_delay=0.01)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = MOCK_LLM_RESPONSE
        mock_response.usage.total_tokens = 1500
        mock_response.usage.prompt_tokens = 1200
        mock_response.usage.completion_tokens = 300

        with patch(
            "apps.ai.services.llm_adapter.litellm_completion",
            return_value=mock_response,
        ):
            llm_result = adapter.chat_completion(
                config=openai_config,
                messages=[
                    {"role": "system", "content": prompt_result["system_prompt"]},
                    {"role": "user", "content": prompt_result["user_prompt"]},
                ],
            )

        assert llm_result.content == MOCK_LLM_RESPONSE
        assert llm_result.total_tokens == 1500

        # 3. 解析响应
        parser = ResponseParser()
        parsed = parser.parse(llm_result.content)

        assert parsed.summary == "发现 SQL 注入漏洞和明文密码比较问题，建议立即修复安全相关代码。"
        assert len(parsed.issues) == 3

        # 验证第一个 issue（SQL 注入）
        sql_issue = parsed.issues[0]
        assert sql_issue.file_path == "app.py"
        assert sql_issue.start_line == 8
        assert sql_issue.severity == "critical"
        assert sql_issue.dimension == "security"
        assert sql_issue.confidence == 0.95
        assert sql_issue.code_snippet is not None
        assert sql_issue.fix_snippet is not None

        # 验证第二个 issue（明文密码）
        pw_issue = parsed.issues[1]
        assert pw_issue.severity == "critical"
        assert pw_issue.confidence == 0.92

        # 验证低信心度 issue 仍被保留
        low_conf = parsed.issues[2]
        assert low_conf.confidence == 0.4
        assert low_conf.severity == "medium"

    def test_pipeline_with_malformed_response(
        self, openai_config, sample_files
    ):
        """LLM 返回包含在 markdown 代码块中的 JSON"""
        engine = PromptEngine()
        prompt_result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=sample_files,
        )

        malformed_response = (
            "以下是审查结果：\n\n"
            "```json\n"
            '{"summary": "代码审查完成", "issues": []}\n'
            "```\n"
        )

        adapter = LLMAdapter(max_retries=1, retry_delay=0.01)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = malformed_response
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 80
        mock_response.usage.completion_tokens = 20

        with patch(
            "apps.ai.services.llm_adapter.litellm_completion",
            return_value=mock_response,
        ):
            llm_result = adapter.chat_completion(
                config=openai_config,
                messages=[
                    {"role": "system", "content": prompt_result["system_prompt"]},
                    {"role": "user", "content": prompt_result["user_prompt"]},
                ],
            )

        parser = ResponseParser()
        parsed = parser.parse(llm_result.content)
        assert parsed.summary == "代码审查完成"
        assert len(parsed.issues) == 0

    def test_pipeline_handles_llm_error(self, openai_config, sample_files):
        """LLM 调用失败时的处理"""
        from apps.ai.services.llm_adapter import LLMCallError

        engine = PromptEngine()
        prompt_result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=[],
            files=sample_files,
        )

        adapter = LLMAdapter(max_retries=2, retry_delay=0.01)
        with patch(
            "apps.ai.services.llm_adapter.litellm_completion",
            side_effect=Exception("API timeout"),
        ):
            with pytest.raises(LLMCallError):
                adapter.chat_completion(
                    config=openai_config,
                    messages=[
                        {"role": "system", "content": prompt_result["system_prompt"]},
                        {"role": "user", "content": prompt_result["user_prompt"]},
                    ],
                )


class TestTokenBudgetIntegration:
    """Token 预算计算集成测试"""

    def test_calculate_available_budget(self, sample_files):
        from apps.ai.services.token_manager import TokenManager

        engine = PromptEngine()
        token_mgr = TokenManager()

        prompt_result = engine.build_review_prompt(
            project_type="python",
            primary_language="Python",
            frameworks=["flask"],
            files=sample_files,
        )

        system_tokens = token_mgr.count_tokens(prompt_result["system_prompt"])
        user_tokens = token_mgr.count_tokens(prompt_result["user_prompt"])

        budget = token_mgr.calculate_available_budget(
            model="gpt-4o",
            system_prompt=prompt_result["system_prompt"],
            user_content=prompt_result["user_prompt"],
            output_reserve=2000,
        )

        assert budget > 0
        assert budget == 128000 - system_tokens - user_tokens - 2000
