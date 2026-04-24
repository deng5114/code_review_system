# Phase 1 Step 3: AI 集成层 — 实施计划

## 目标

实现单模型 AI 调用，打通 Prompt 组装和结果解析。配置一个 API Key 后，能成功调用模型并解析返回结构化审查结果。

## 实施步骤（TDD 驱动）

### 阶段 A: Token 管理器（最简单，无外部依赖）

1. **tests/test_token_manager.py** — 先写测试 (RED)
   - 计算 Python/TypeScript/Markdown 文本的 token 数
   - 模型上下文窗口限制查询
   - 文本截断到指定 token 数
   - 空文本、超长文本边界情况
2. **services/token_manager.py** — 实现 (GREEN)
   - `TokenManager` 类：基于 tiktoken 的 token 计算
   - `MODEL_CONTEXT_WINDOWS` 常量映射
   - `count_tokens(text, model)` 方法
   - `truncate_to_tokens(text, max_tokens)` 方法
   - `get_model_context_window(model)` 方法

### 阶段 B: 响应解析器

3. **tests/test_response_parser.py** — 先写测试 (RED)
   - 解析标准 JSON 格式的 AI 响应
   - 容错：从 markdown 代码块中提取 JSON
   - 容错：修复常见的 AI 输出格式问题（尾逗号、单引号、注释）
   - 验证解析结果的 schema（严重性、维度等）
   - 解析失败返回有意义的错误
4. **services/response_parser.py** — 实现 (GREEN)
   - `ResponseParser` 类
   - `_extract_json_from_text()` — 从任意文本提取 JSON
   - `_fix_common_json_errors()` — 修复常见格式错误
   - `parse_review_response()` — 解析审查结果为结构化数据
   - `validate_issue()` — 验证单个 issue 的字段

### 阶段 C: Prompt 模板

5. **prompts/system_base.txt** — 基础 System Prompt
   - 角色定义：你是专业的代码审查专家
   - 7 维度审查矩阵：security, correctness, performance, maintainability, type_safety, completeness, best_practices
   - 严重性分级标准：critical/high/medium/low
   - 信心度评估要求：0.0-1.0
6. **prompts/user_review.txt** — User Prompt 模板（Jinja2）
   - 项目信息区（项目类型、语言、框架）
   - 代码文件区（文件路径、语言、代码内容）
   - 用户自定义指令区（可选）
   - 输出格式要求（JSON schema）
7. **prompts/output_schema.json** — 输出格式定义

### 阶段 D: Prompt 引擎

8. **tests/test_prompt_engine.py** — 先写测试 (RED)
   - 加载模板文件
   - Jinja2 渲染（变量替换）
   - 动态组装（基础 + 语言专项 + 用户指令）
   - 缺少模板变量时的错误处理
9. **services/prompt_engine.py** — 实现 (GREEN)
   - `PromptEngine` 类
   - `build_review_prompt()` — 组装完整审查 prompt
   - `_load_template()` — 加载模板文件
   - `_render()` — Jinja2 渲染

### 阶段 E: LLM 适配器

10. **tests/test_llm_adapter.py** — 先写测试 (RED)
    - mock litellm 调用，验证参数正确传递
    - 重试逻辑测试（模拟失败 → 重试 → 成功）
    - 重试次数耗尽后抛出异常
    - 支持 different providers（openai, anthropic, ollama）
11. **services/llm_adapter.py** — 实现 (GREEN)
    - `LLMAdapter` 类
    - `chat_completion()` — 统一调用接口
    - `_build_litellm_params()` — 构建 litellm 参数
    - `_retry_with_backoff()` — 指数退避重试（最多 3 次）
    - 使用 AIConfig 模型获取 provider/model/key 配置

### 阶段 F: AI 配置 API

12. **ai/serializers.py** — AIConfigSerializer、AITestConnectionSerializer
13. **ai/views.py** — AIConfigViewSet (CRUD + test_connection)
14. **ai/urls.py** — 更新路由

### 阶段 G: 集成测试与验证

15. **tests/test_integration.py** — 端到端集成测试（mock LLM）
    - 组装 prompt → 调用 LLM（mock）→ 解析响应 → 验证结构
16. **覆盖率验证** — pytest --cov >= 80%

## 新建文件（16 个）

```
backend/
├── apps/ai/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── token_manager.py
│   │   ├── response_parser.py
│   │   ├── prompt_engine.py
│   │   └── llm_adapter.py
│   ├── prompts/
│   │   ├── system_base.txt
│   │   ├── user_review.txt
│   │   └── output_schema.json
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_token_manager.py
│   │   ├── test_response_parser.py
│   │   ├── test_prompt_engine.py
│   │   ├── test_llm_adapter.py
│   │   └── test_integration.py
│   ├── serializers.py
│   └── views.py (修改)
```

## 依赖顺序

```
token_manager → prompt_engine → llm_adapter → integration
response_parser ──────────────↗
prompt templates ──→ prompt_engine
```

## 风险识别

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| tiktoken 对非 OpenAI 模型不精确 | MEDIUM | 使用估算系数 fallback |
| litellm API 不稳定 | MEDIUM | 重试机制 + 详细错误日志 |
| AI 输出格式不可控 | HIGH | 多层容错解析器 |
| 测试需要 mock LLM 调用 | LOW | 使用 unittest.mock |

## 验收标准

1. 配置 OpenAI API Key → 能成功调用 gpt-4o
2. 输入 Python 代码 → Prompt 正确组装
3. LLM 返回 JSON → 正确解析为 ReviewIssue 列表
4. LLM 返回非标准格式 → 容错解析成功
5. Token 计算 → 精确度 > 95%（对比实际）
6. 测试覆盖率 >= 80%
