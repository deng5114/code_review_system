# Phase 2 实施计划 — 功能完善与增强

> 版本: 1.0 | 日期: 2026-04-26
> 状态: 待确认

---

## 概述

Phase 2 在 Phase 1 MVP（上传 → 解析 → AI 审查 → 查看结果）的基础上，增强用户体验、AI 能力、安全性和实时性。将功能重新组织为 **6 个可独立交付的阶段**，每个阶段都有明确的验收标准。

### Phase 1 已完成回顾

| 指标 | 数值 |
|------|------|
| 后端测试 | 209 个，96% 覆盖率 |
| 前端页面 | 5 个 |
| 代码行数 | 11,382 行 |
| Git 提交 | 5 次 |

### 关键现状分析

| 功能 | 状态 | 说明 |
|------|------|------|
| LiteLLM 多模型 | ✅ 已集成 | 6 个提供商，仅缺降级策略 |
| 审查结果筛选 API | ✅ 已支持 | severity/dimension/file_path |
| ECharts | ✅ 已安装 | 未创建任何图表组件 |
| Markdown 报告 | ✅ 后端已生成 | 前端缺下载按钮 |
| Prompt 模板 | ✅ 基础模板 | 无语言专项模板 |
| API Key 加密 | ⚠️ HMAC | 需升级到 AES-GCM |
| 前端测试 | ❌ 无 | 需要 Vitest + Playwright |
| 实时进度 | ⚠️ 轮询 | 需要 WebSocket |

---

## 阶段总览

```
阶段 2.1: 用户体验增强（筛选、导出、图表）     ← 优先级高，2-3天
阶段 2.2: AI 能力增强（语言Prompt、降级策略）  ← 优先级高，3-4天
阶段 2.3: 安全升级（AES-GCM 加密）             ← 优先级中，1-2天
阶段 2.4: 实时性提升（WebSocket 进度推送）     ← 优先级中，2-3天
阶段 2.5: 前端测试（Vitest + Playwright）      ← 优先级高，2-3天
阶段 2.6: 性能优化（代码分割、懒加载）          ← 优先级低，1-2天
```

---

## 阶段 2.1：用户体验增强

> **目标**: 提升审查结果的可视化和交互体验
> **预计工作量**: 2-3 天

### 2.1.1 高级筛选面板 (FilterPanel)

**现状**: 后端 API 已支持筛选参数，前端仅有基础 Select 组件

**新增文件**: `frontend/src/components/FilterPanel.tsx`

功能要求：
- 严重性多选（critical/high/medium/low）
- 维度多选（7 个维度）
- 文件路径搜索（模糊匹配）
- 关键词搜索（标题和描述中搜索）
- 快捷预设按钮（"仅安全问题"、"所有高级别"）
- 筛选结果数量统计
- 清空筛选按钮
- URL 参数持久化

**修改文件**: `frontend/src/pages/ReviewDashboard.tsx`（替换现有 Select 组件）

**后端增强**: `backend/apps/reviews/views.py`（添加 keyword 参数、severity__in/dimension__in 批量查询）

### 2.1.2 报告导出

**现状**: 后端 `report_generator.py` 已生成 Markdown，API `/report/` 已存在

**新增方法**: `frontend/src/api/reviews.ts` — `downloadReport(reviewId, format)`

功能要求：
- 支持 Markdown 格式下载
- 文件名包含 reviewId 和日期
- 支持中文文件名
- 大文件不阻塞 UI

**修改文件**: `frontend/src/pages/ReviewDashboard.tsx`（添加导出按钮）

### 2.1.3 项目概览仪表盘

**现状**: ECharts 已安装但未使用

**新增文件**:
- `frontend/src/components/charts/LanguagePieChart.tsx` — 语言分布饼图
- `frontend/src/components/charts/SeverityBarChart.tsx` — 严重性分布柱状图
- `frontend/src/components/charts/DimensionHeatmap.tsx` — 维度×严重性热力图

功能要求：
- 响应式布局
- 颜色与 SEVERITY_CONFIG 一致
- 空数据友好提示
- 点击热力图单元格跳转筛选

**修改文件**: `frontend/src/pages/ProjectOverview.tsx`（集成图表）

### 阶段 2.1 验收标准

- [ ] FilterPanel 多维度筛选正常工作
- [ ] URL 参数保持筛选状态
- [ ] 点击导出按钮成功下载 Markdown 文件
- [ ] 三个图表正确显示数据
- [ ] 响应式布局在移动端正常

---

## 阶段 2.2：AI 能力增强

> **目标**: 提升 AI 审查的准确性和可靠性
> **预计工作量**: 3-4 天

### 2.2.1 语言专项 Prompt 模板

**现状**: 仅基础 Prompt 模板（system_base.txt, user_review.txt）

**新增文件**（5 个语言专项模板）:
- `backend/apps/ai/prompts/language_specific/python.txt`
- `backend/apps/ai/prompts/language_specific/typescript.txt`
- `backend/apps/ai/prompts/language_specific/go.txt`
- `backend/apps/ai/prompts/language_specific/java.txt`
- `backend/apps/ai/prompts/language_specific/rust.txt`

每个模板包含：
- 语言特定的常见问题检查清单
- 框架特定的审查重点
- 最佳实践提醒

**修改文件**:
- `backend/apps/ai/services/prompt_engine.py` — 添加 `_load_language_specific_guidance()` 方法
- `backend/apps/ai/prompts/user_review.txt` — 添加 `language_guidance` 变量

**新增测试**: `backend/apps/ai/tests/test_prompt_engine_languages.py`

### 2.2.2 模型降级策略

**现状**: AIConfig 支持多配置但无降级机制

**新增文件**:
- `backend/apps/ai/services/llm_call_manager.py` — LLMCallManager 类

核心逻辑：
```
调用主配置 → 失败 → 按优先级尝试备用配置（最多 N 个）→ 全部失败则抛出异常
```

**修改文件**:
- `backend/apps/ai/models.py` — 添加 `priority`、`fallback_enabled` 字段
- `backend/apps/reviews/services/review_engine.py` — 使用 LLMCallManager
- `frontend/src/pages/Settings.tsx` — 添加优先级和降级开关

**新增测试**: `backend/apps/ai/tests/test_llm_call_manager.py`

### 阶段 2.2 验收标准

- [ ] 5 个语言专项模板加载正确
- [ ] 不支持的语言优雅降级
- [ ] 主模型失败时自动切换备用
- [ ] 降级事件在日志中可见
- [ ] 所有新测试通过，覆盖率 > 90%

---

## 阶段 2.3：安全升级

> **目标**: 将 API Key 加密从 HMAC 升级到 AES-GCM
> **预计工作量**: 1-2 天

### 新增文件

- `backend/apps/common/services/crypto.py` — AESEncryption 工具类
- `backend/apps/common/tests/test_crypto.py` — 加密测试
- `backend/apps/ai/migrations/000X_migrate_to_aes_gcm.py` — 数据迁移

### 修改文件

- `backend/apps/ai/models.py` — API Key 使用 AES-GCM 加密
- `backend/requirements.txt` — 添加 `cryptography>=42.0.0`
- `backend/.env.example` — 添加 AES_ENCRYPTION_KEY 说明

### 实施要点

- 使用 `cryptography` 库的 AESGCM
- 32 字节密钥从环境变量获取
- 数据迁移脚本：Django signing → AES-GCM
- 保留回滚迁移

### 阶段 2.3 验收标准

- [ ] AES-GCM 加密/解密正确
- [ ] 数据迁移脚本执行成功
- [ ] 迁移后 API Key 正常使用
- [ ] 测试覆盖率 > 95%

---

## 阶段 2.4：实时性提升

> **目标**: 使用 WebSocket 替代轮询推送审查进度
> **预计工作量**: 2-3 天

### 后端

**新增文件**:
- `backend/apps/reviews/consumers.py` — ReviewProgressConsumer
- `backend/config/routing.py` — WebSocket 路由

**修改文件**:
- `backend/config/settings.py` — 添加 channels 配置
- `backend/config/asgi.py` — 集成 WebSocket 路由
- `backend/apps/reviews/tasks.py` — 通过 Channel Layer 推送进度
- `backend/requirements.txt` — 添加 channels、channels-redis

WebSocket 路由：`ws/reviews/{review_id}/progress/`

### 前端

**新增文件**:
- `frontend/src/hooks/useReviewWebSocket.ts` — WebSocket Hook

**修改文件**:
- `frontend/src/stores/reviewStore.ts` — 添加 `updateReviewProgress` 方法
- `frontend/src/pages/ReviewDashboard.tsx` — 使用 WebSocket 替代轮询

### 降级策略

- WebSocket 连接失败 → 自动降级到轮询
- 组件卸载时关闭连接
- 重连机制

### 阶段 2.4 验收标准

- [ ] WebSocket 连接正常建立
- [ ] 进度实时推送（无轮询请求）
- [ ] 连接断开时降级到轮询
- [ ] 组件卸载时连接关闭

---

## 阶段 2.5：前端测试

> **目标**: 为前端添加测试覆盖
> **预计工作量**: 2-3 天

### 2.5.1 Vitest 单元测试

**新增文件**:
- `frontend/vitest.config.ts` — Vitest 配置
- `frontend/src/test/setup.ts` — 测试环境初始化
- `frontend/src/components/__tests__/FilterPanel.test.tsx`
- `frontend/src/components/charts/__tests__/LanguagePieChart.test.tsx`
- `frontend/src/stores/__tests__/projectStore.test.ts`
- `frontend/src/stores/__tests__/reviewStore.test.ts`
- `frontend/src/api/__tests__/projects.test.ts`
- `frontend/src/api/__tests__/reviews.test.ts`

新增依赖：vitest, @testing-library/react, @testing-library/jest-dom, jsdom

### 2.5.2 Playwright E2E 测试

**新增文件**:
- `frontend/playwright.config.ts`
- `frontend/e2e/upload.spec.ts` — 上传流程
- `frontend/e2e/review.spec.ts` — 审查流程
- `frontend/e2e/filter.spec.ts` — 筛选功能

新增依赖：@playwright/test

### 阶段 2.5 验收标准

- [ ] 单元测试覆盖率 > 80%
- [ ] E2E 测试覆盖核心流程
- [ ] 测试运行时间 < 5 分钟

---

## 阶段 2.6：性能优化

> **目标**: 优化前端构建和运行时性能
> **预计工作量**: 1-2 天

### 代码分割

**修改文件**: `frontend/src/App.tsx` — 路由级 lazy()

**修改文件**: `frontend/vite.config.ts` — manualChunks 配置

分包策略：
- react-vendor: react, react-dom, react-router-dom
- antd-vendor: antd, @ant-design/icons
- monaco-vendor: monaco-editor, @monaco-editor/react
- echarts-vendor: echarts, echarts-for-react

### 阶段 2.6 验收标准

- [ ] 首屏加载 < 2 秒
- [ ] 主 bundle < 500KB
- [ ] 路由切换流畅
- [ ] Lighthouse 性能评分 > 90

---

## 新增文件汇总

```
backend/
  apps/
    ai/
      prompts/language_specific/
        python.txt
        typescript.txt
        go.txt
        java.txt
        rust.txt
      services/llm_call_manager.py
      tests/test_llm_call_manager.py
      tests/test_prompt_engine_languages.py
      migrations/000X_add_fallback_fields.py
      migrations/000X_migrate_to_aes_gcm.py
    common/
      services/crypto.py
      tests/test_crypto.py
    reviews/
      consumers.py
  config/routing.py

frontend/
  src/
    components/FilterPanel.tsx
    components/charts/LanguagePieChart.tsx
    components/charts/SeverityBarChart.tsx
    components/charts/DimensionHeatmap.tsx
    hooks/useReviewWebSocket.ts
    test/setup.ts
    components/__tests__/FilterPanel.test.tsx
    components/charts/__tests__/LanguagePieChart.test.tsx
    stores/__tests__/projectStore.test.ts
    stores/__tests__/reviewStore.test.ts
    api/__tests__/projects.test.ts
    api/__tests__/reviews.test.ts
  e2e/
    upload.spec.ts
    review.spec.ts
    filter.spec.ts
  vitest.config.ts
  playwright.config.ts
```

## 修改文件汇总

```
backend/
  apps/ai/models.py                          — priority, fallback_enabled, AES-GCM
  apps/ai/services/prompt_engine.py           — 语言专项模板加载
  apps/ai/prompts/user_review.txt             — language_guidance 变量
  apps/reviews/services/review_engine.py      — LLMCallManager
  apps/reviews/tasks.py                       — WebSocket 进度推送
  apps/reviews/views.py                       — keyword 搜索
  config/settings.py                          — channels 配置
  config/asgi.py                              — WebSocket 路由
  requirements.txt                            — channels, cryptography

frontend/
  src/pages/ReviewDashboard.tsx               — FilterPanel + 导出按钮 + WebSocket
  src/pages/ProjectOverview.tsx               — 图表集成
  src/pages/Settings.tsx                      — 优先级和降级配置
  src/stores/reviewStore.ts                   — updateReviewProgress
  src/api/reviews.ts                          — downloadReport
  src/App.tsx                                 — lazy 路由
  vite.config.ts                              — manualChunks
  package.json                                — 测试依赖
```

## 依赖变更

### Python 新增

```
cryptography>=42.0.0
channels>=4.0.0
channels-redis>=4.0.0
```

### 前端新增

```
vitest@^2.0.0
@vitest/ui@^2.0.0
@testing-library/react@^16.0.0
@testing-library/jest-dom@^6.4.0
@testing-library/user-event@^14.5.0
jsdom@^24.0.0
@playwright/test@^1.45.0
```

### 环境变量新增

```bash
AES_ENCRYPTION_KEY=<64位十六进制字符串>
```

---

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| AES-GCM 数据迁移失败 | 高 | 充分测试迁移脚本，保留回滚方案 |
| WebSocket 连接不稳定 | 中 | 降级到轮询机制 |
| E2E 测试脆弱 | 中 | 稳定选择器，重试逻辑 |
| 模型降级逻辑复杂 | 中 | 充分单元测试，逐步实现 |
| 语言专项 Prompt 效果不佳 | 低 | 收集反馈迭代 |

---

## 实施时间线

```
Week 1-2: 阶段 2.1 用户体验增强
Week 3-4: 阶段 2.2 AI 能力增强
Week 5:   阶段 2.3 安全升级
Week 6:   阶段 2.4 实时性提升
Week 7-8: 阶段 2.5 前端测试
Week 9:   阶段 2.6 性能优化
Week 10:  集成测试与发布
```

---

## Phase 2 验收总标准

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 切换模型 | 从 GPT-4o 切到 Claude | 审查完成，结果格式一致 |
| 模型降级 | 主模型不可用 | 自动使用备用模型，审查正常 |
| 筛选问题 | 筛选 CRITICAL + security | 仅显示安全相关严重问题 |
| 导出报告 | 点击导出 Markdown | 下载完整报告文件 |
| 语言专项 | 审查 Python 项目 | Prompt 包含 Python 特定审查重点 |
| 实时进度 | 发起审查 | WebSocket 推送进度，无轮询 |
| 前端测试 | 运行 vitest | 覆盖率 > 80% |
