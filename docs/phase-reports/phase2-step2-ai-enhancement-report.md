# Phase 2 Step 2 报告 — AI 能力增强

**项目**: CodeReview Pro — AI 驱动的代码审查系统
**阶段**: Phase 2 Step 2 — AI 能力增强
**日期**: 2026-04-26
**状态**: 已完成

---

## 一、实施目标

提升 AI 审查的准确性和可靠性，通过语言专项 Prompt 模板增强审查针对性，通过模型降级策略提升系统鲁棒性。

---

## 二、变更总览

### 2.1 语言专项 Prompt 模板

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/apps/ai/prompts/language_specific/python.txt` | 新增 | Python 语言审查指南（安全、Django/Flask/FastAPI、最佳实践） |
| `backend/apps/ai/prompts/language_specific/typescript.txt` | 新增 | TypeScript/JavaScript 审查指南（XSS、React/Next.js/Vue、最佳实践） |
| `backend/apps/ai/prompts/language_specific/go.txt` | 新增 | Go 语言审查指南（竞态、Gin/Echo、最佳实践） |
| `backend/apps/ai/prompts/language_specific/java.txt` | 新增 | Java 语言审查指南（SQL 注入、Spring Boot/JPA、最佳实践） |
| `backend/apps/ai/prompts/language_specific/rust.txt` | 新增 | Rust 语言审查指南（unsafe、Tokio/axum、最佳实践） |
| `backend/apps/ai/prompts/user_review.txt` | 修改 | 添加 `language_guidance` 变量块 |
| `backend/apps/ai/services/prompt_engine.py` | 修改 | 新增 `_load_language_specific_guidance()` 方法；路径遍历防护（正则白名单）；Jinja2 沙箱环境 |
| `backend/apps/ai/tests/test_prompt_engine_languages.py` | 新增 | 11 个测试用例 |

### 2.2 模型降级策略

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/apps/ai/services/llm_call_manager.py` | 新增 | LLMCallManager 降级管理器（adapter 必填注入） |
| `backend/apps/ai/models.py` | 修改 | 添加 `priority`（含 MinValueValidator/MaxValueValidator）、`fallback_enabled` 字段 |
| `backend/apps/ai/serializers.py` | 修改 | 序列化器包含新字段 |
| `backend/apps/ai/migrations/0003_add_priority_and_fallback_fields.py` | 新增 | 数据库迁移 |
| `backend/apps/reviews/services/review_engine.py` | 修改 | 接收 `LLMConfig` + `fallback_configs` 参数；ORM 查询移至调用方；chunk 级即时日志记录 |
| `backend/apps/reviews/tasks.py` | 修改 | 调用方构建 fallback chain（数据库排序 + 数量上限 5） |
| `backend/apps/ai/tests/test_llm_call_manager.py` | 新增 | 11 个测试用例 |
| `backend/apps/reviews/tests/test_review_engine.py` | 修改 | 适配新的 LLMCallManager + LLMConfig 签名 |

### 2.3 前端配置界面

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/types/index.ts` | 修改 | AIConfig/AIConfigCreate 添加 priority、fallback_enabled |
| `frontend/src/pages/Settings.tsx` | 修改 | 表格添加优先级/降级列，表单添加优先级输入和降级开关（含 Tooltip） |

---

## 三、代码统计

| 指标 | 数值 |
|------|------|
| 新增文件数 | 9 |
| 修改文件数 | 8 |
| 新增后端代码行 | ~420 |
| 新增前端代码行 | ~50 |
| 新增测试用例 | 22 |
| 后端累计测试数 | 240 |

---

## 四、功能详情

### 4.1 语言专项 Prompt 模板

5 种语言专项模板，每种包含：
- **常见安全问题** — 语言特定的安全风险检查清单
- **框架审查重点** — 主流框架的专项审查要点
- **最佳实践** — 语言惯用写法和推荐模式

支持语言别名映射（javascript→typescript, py→python, golang→go, kt/kotlin/scala→java 等），不支持的语言优雅降级（不注入任何指南内容）。

**安全措施**：
- `_SAFE_LANGUAGE_RE` 正则白名单校验，阻止路径遍历攻击
- 使用 `SandboxedEnvironment` 防止用户代码中的 Jinja2 模板注入

### 4.2 模型降级策略

**LLMCallManager 核心逻辑**：
1. 调用主配置
2. 失败后按优先级降序尝试备用配置（最多 N 个，默认 3）
3. 全部失败则抛出异常
4. 每次降级事件记录到 `fallback_logs`（每次 `chat_completion` 清空，由调用方即时消费）

**架构决策**：
- ReviewEngine 不直接查询数据库，接收 `LLMConfig` + `fallback_configs` 参数
- ORM 查询由 `tasks.py` 完成（使用 `order_by("-priority")[:5]` 数据库排序 + 数量上限）
- `LLMCallManager` 的 `adapter` 参数为必填，强制依赖注入
- `ReviewEngine` 构造函数支持可选 `llm_manager` 注入

**降级日志**：在 chunk 循环内即时记录，避免多 chunk 场景下日志丢失。

### 4.3 前端配置

Settings 页面新增：
- 优先级数值输入（0-100，Tooltip 说明）
- 降级启用开关（Tooltip 说明）
- 表格展示优先级标签和降级状态标签

---

## 五、测试结果

| 测试类型 | 结果 |
|----------|------|
| 后端 pytest (240 tests) | 全部通过 |
| TypeScript 类型检查 | 通过 |
| Vite 构建 | 通过 |

新增测试覆盖：

**语言专项模板 (11 tests)**：
- 5 种支持语言加载正确
- 语言关键词匹配
- 不支持语言优雅降级
- 大小写不敏感匹配
- 别名映射（javascript→typescript, py→python, golang→go）
- 指南出现在代码之前
- 自定义指令与语言指南共存
- 路径遍历攻击拒绝（`../../etc/passwd`）
- 斜杠路径遍历拒绝（`../system_base`）

**LLMCallManager (11 tests)**：
- 主配置成功直接返回
- 主配置失败自动降级
- 所有配置失败抛出异常
- max_fallbacks 限制尝试数量
- 无备用配置时抛出原始错误
- 日志每次调用清空
- 第二个备用配置成功
- 降级链按优先级排序
- 过滤不活跃配置
- 过滤未启用降级的配置
- 空输入返回空链

---

## 六、代码审查

4 个并行审查代理（AI 层后端、Review Engine、前端、测试文件）共发现 7 个 HIGH 问题，全部已在本次提交前修复：

| # | 问题 | 修复方式 |
|---|------|----------|
| 1 | 路径遍历风险（`primary_language` 未校验） | 添加 `_SAFE_LANGUAGE_RE` 正则白名单 |
| 2 | Jinja2 非沙箱环境 | 改用 `SandboxedEnvironment` |
| 3 | 残留 `LLMAdapter` 导入 | 清理无用导入 |
| 4 | ReviewEngine 与 Django ORM 紧耦合 | 将 ORM 查询移至 `tasks.py`，ReviewEngine 接收纯数据 |
| 5 | 多 chunk 场景 fallback_logs 丢失 | 日志记录移至 chunk 循环内部即时消费 |
| 6 | 缺少 `custom_instructions` 和路径遍历测试 | 新增 3 个测试 |
| 7 | `LLMCallManager` adapter=None 默认值 | 改为必填参数，强制依赖注入 |

额外修复 MEDIUM 问题：`priority` 字段添加 `MinValueValidator(0)` + `MaxValueValidator(100)`。

---

## 七、已知限制

| 限制 | 计划 |
|------|------|
| 降级不跨 chunk 持久化 | 后续优化：chunk 级别记住成功的备用配置 |
| 前端降级事件不可见 | 后续通过 WebSocket 推送降级通知 |
| 语言模板未支持 C/C++ | 按需扩展 |

---

## 八、下一步

Phase 2 Step 3: 安全升级
- AES-GCM 加密替代 Django signing
- API Key 数据迁移
