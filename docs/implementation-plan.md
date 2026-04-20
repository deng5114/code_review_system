# CodeReview Pro — 实施计划

> 版本: 1.0 | 日期: 2026-04-20

---

## 实施概览

```
Phase 1: MVP（核心可用）         ← 当前重点
Phase 2: 完善（多模型 + 筛选）
Phase 3: 增强（高级功能）
```

---

## Phase 1 — MVP

> 目标: 上传压缩包 → AI 审查 → 查看结果，核心链路打通

### Step 1: Django 项目脚手架

**目标**: 搭建 Django 后端基础结构

**任务清单**:
- [ ] 创建 Django 项目 `config/`
- [ ] 创建 4 个 app: `projects`, `reviews`, `ai`, `common`
- [ ] 配置 SQLite 数据库
- [ ] 配置 DRF（Django REST Framework）
- [ ] 配置 CORS（允许前端跨域）
- [ ] 配置 media 文件存储路径
- [ ] 创建基础模型（见 architecture.md 3.2）
- [ ] 执行 migrate，验证数据库创建

**关键文件**:
```
backend/
├── config/settings.py
├── config/urls.py
├── apps/projects/models.py
├── apps/reviews/models.py
├── apps/ai/models.py
├── apps/common/models.py
└── manage.py
```

**验收**: `python manage.py runserver` 正常启动，数据库表创建成功

### Step 2: 项目上传与解析服务

**目标**: 实现压缩包上传、解压、项目检测

**任务清单**:
- [ ] `projects/services/zip_parser.py`
  - 支持 .zip / .tar.gz / .tar.bz2
  - 安全检查: 解压炸弹、路径穿越
  - 排除规则: node_modules/, .git/, venv/ 等
- [ ] `projects/services/project_detector.py`
  - 扫描配置文件识别项目类型
  - 统计语言分布（按文件扩展名）
  - 识别框架
- [ ] `projects/services/file_filter.py`
  - 过滤二进制文件
  - 过滤第三方/生成代码
  - 返回可审查文件列表
- [ ] `projects/views.py` — 上传 API
  - POST /api/projects/upload/
  - GET /api/projects/
  - GET /api/projects/{id}/
  - GET /api/projects/{id}/files/
  - GET /api/projects/{id}/files/{path}/
- [ ] `projects/serializers.py`

**验收**: 上传一个 TypeScript 项目 zip，能正确识别项目类型、语言分布，返回文件树

### Step 3: AI 集成层

**目标**: 实现单模型 AI 调用，打通 Prompt 组装和结果解析

**任务清单**:
- [ ] `ai/models.py` — AIConfig 模型
- [ ] `ai/services/llm_adapter.py`
  - 集成 litellm
  - chat_completion() 统一接口
  - 重试逻辑（最多 3 次）
- [ ] `ai/services/prompt_engine.py`
  - Prompt 模板加载和 Jinja2 渲染
  - 动态组装: 基础 + 语言专项 + 用户指令
- [ ] `ai/services/response_parser.py`
  - JSON 输出解析（多层容错）
  - 常见 AI 输出格式修复
- [ ] `ai/services/token_manager.py`
  - tiktoken 计算 token 数
  - 模型上下文窗口管理
- [ ] `ai/prompts/system_base.txt` — 基础 System Prompt
- [ ] `ai/prompts/user_review.txt` — User Prompt 模板
- [ ] `ai/prompts/output_schema.json` — 输出格式定义
- [ ] `ai/views.py` — AI 配置 CRUD API

**验收**: 配置一个 OpenAI API Key，能成功调用模型并解析返回结果

### Step 4: 审查引擎核心

**目标**: 实现完整的 8 阶段审查流水线

**任务清单**:
- [ ] `reviews/services/review_engine.py` — 核心调度器
  - 8 阶段流水线实现
  - Celery 异步任务集成
- [ ] `reviews/services/chunk_manager.py`
  - 三级分片策略（全量/分组/分片）
  - 按语言/模块分组逻辑
- [ ] `reviews/services/result_aggregator.py`
  - 问题去重
  - 同类合并
  - 严重性校验
- [ ] `reviews/services/report_generator.py`
  - Markdown 报告生成
  - JSON 结构化输出
- [ ] `reviews/tasks.py` — Celery 异步任务
- [ ] `reviews/views.py` — 审查 API
  - POST /api/projects/{id}/reviews/
  - GET /api/reviews/{id}/
  - GET /api/reviews/{id}/issues/

**验收**: 上传一个小型 Python 项目，发起审查，能返回结构化的审查结果

### Step 5: React 前端 — 上传与概览

**目标**: 实现上传页面和项目概览页面

**任务清单**:
- [ ] Vite + React + TypeScript 项目脚手架
- [ ] Ant Design 集成
- [ ] Zustand 状态管理配置
- [ ] API 调用封装（axios）
- [ ] Upload 页面
  - 拖拽上传组件
  - 上传进度展示
  - 解析状态轮询
- [ ] ProjectOverview 页面
  - 项目信息卡片
  - 文件树组件
  - 语言分布统计
  - 发起审查按钮

**验收**: 上传 zip 文件，前端显示项目概览、文件树、语言统计

### Step 6: React 前端 — 审查结果展示

**目标**: 实现代码查看器和审查报告展示

**任务清单**:
- [ ] ReviewDashboard 页面
  - 审查进度条
  - 问题总数 + 严重性分布
  - AI 总体评估
- [ ] CodeViewer 组件
  - Monaco Editor 只读模式
  - 行级别问题标注（高亮 + 悬停卡片）
  - 严重性颜色标记
- [ ] IssueCard 组件
  - 严重性标签 + 维度标签
  - 问题描述 + 修复建议
  - 代码对比（问题代码 vs 修复代码）
- [ ] FileTree 组件
  - 文件旁标注问题数量
  - 点击切换代码视图
- [ ] 审查进度轮询

**验收**: 审查完成后，前端能展示代码行标注、问题卡片、审查摘要

---

## Phase 2 — 完善

> 目标: 多模型支持 + 筛选 + 导出

### Step 7: 多 AI 模型支持

- [ ] LiteLLM 完整集成（OpenAI/Claude/Gemini/DeepSeek/Ollama）
- [ ] AI 配置管理界面（Settings 页面）
- [ ] API Key 加密存储
- [ ] 连接测试功能
- [ ] 模型降级策略（主模型失败切换备用）

### Step 8: 审查结果筛选

- [ ] FilterPanel 组件
  - 严重性多选筛选
  - 维度多选筛选
  - 文件筛选
  - 关键词搜索
- [ ] 筛选 API 参数传递
- [ ] 筛选结果实时更新

### Step 9: 项目概览仪表盘

- [ ] 语言分布饼图（ECharts）
- [ ] 维度热力图
- [ ] 代码统计卡片
- [ ] 依赖列表展示

### Step 10: 报告导出

- [ ] Markdown 格式导出
- [ ] 报告内容: 摘要 + 问题列表 + 严重性分布表
- [ ] 下载按钮和文件命名

### Step 11: 语言专项 Prompt

- [ ] Python 专项 Prompt（PEP 8、Django/FastAPI 模式）
- [ ] TypeScript 专项 Prompt（strict mode、React hooks）
- [ ] Go 专项 Prompt（错误处理、并发模式）
- [ ] Java 专项 Prompt（分层架构、Spring Boot）
- [ ] Rust 专项 Prompt（所有权、unsafe 审计）

---

## Phase 3 — 增强

> 目标: 高级功能和用户体验优化

### Step 12: Token 预算管理优化

- [ ] 精确 Token 计算（不同模型不同 tokenizer）
- [ ] 自适应分片策略
- [ ] 大项目审查进度细分

### Step 13: 审查历史

- [ ] 审查记录列表页面
- [ ] 历史报告查看
- [ ] 同项目多次审查对比
- [ ] 问题数量趋势图

### Step 14: 自定义规则系统

- [ ] 忽略规则配置（文件/目录/规则类型）
- [ ] 严重级别覆盖配置
- [ ] 自定义审查指令输入
- [ ] 规则预设模板

### Step 15: PDF 报告导出

- [ ] PDF 格式报告生成
- [ ] 专业排版（封面、目录、正文）
- [ ] 代码高亮在 PDF 中的呈现

### Step 16: 用户体验优化

- [ ] 深色模式
- [ ] 审查结果分享链接
- [ ] 批量审查队列
- [ ] 快捷键支持

---

## 验证计划

### Phase 1 验收标准

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 上传 TypeScript 项目 | 上传一个 10 文件的 TS 项目 zip | 正确识别为 Node.js 项目，语言分布准确 |
| 上传 Python 项目 | 上传一个 Django 项目 zip | 识别为 Python + Django 框架 |
| 单模型审查 | 使用 OpenAI gpt-4o 审查 | 返回结构化 JSON，包含 7 维度问题 |
| 审查进度 | 观察审查过程 | 进度从 0% 到 100%，状态实时更新 |
| 代码标注 | 打开审查结果中的代码视图 | 问题行高亮，悬停显示问题卡片 |
| 大文件项目 | 上传 50+ 文件项目 | 分片审查正常完成，结果聚合无遗漏 |
| 错误处理 | 使用无效 API Key | 友好错误提示，不崩溃 |

### Phase 2 验收标准

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 切换模型 | 从 GPT-4o 切换到 Claude | 审查正常完成，结果格式一致 |
| 筛选问题 | 筛选 CRITICAL + security | 仅显示安全相关的严重问题 |
| 导出报告 | 点击导出 Markdown | 下载完整审查报告文件 |

---

## 依赖清单

### Python 依赖

```
Django>=5.1
djangorestframework>=3.15
django-cors-headers>=4.4
celery>=5.4
litellm>=1.50
tiktoken>=0.8
Jinja2>=3.1
python-dotenv>=1.0
Pillow>=10.0
```

### 前端依赖

```
react>=18
typescript>=5
vite>=5
antd>=5
@ant-design/icons
@monaco-editor/react
zustand>=4
axios>=1.7
echarts>=5
react-router-dom>=6
```

---

## 目录结构（最终）

```
code_review_system/
├── docs/                          # 项目文档
│   ├── architecture.md            # 架构设计
│   ├── requirements.md            # 需求分析
│   └── implementation-plan.md     # 实施计划
├── backend/                       # Django 后端
│   ├── config/
│   ├── apps/
│   │   ├── projects/
│   │   ├── reviews/
│   │   ├── ai/
│   │   └── common/
│   ├── manage.py
│   ├── requirements.txt
│   └── db.sqlite3
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── stores/
│   │   ├── api/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
├── opensource-project/            # 参考的开源项目
│   ├── everything-claude-code/
│   └── pr-agent/
└── README.md
```
