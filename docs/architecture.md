# CodeReview Pro — 系统架构设计文档

> 版本: 1.0 | 日期: 2026-04-20
>
> 核心参考项目: [everything-claude-code](https://github.com/anthropics/everything-claude-code) (ECC) · [PR-Agent](https://github.com/Codium-ai/pr-agent)

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                         │
│   Upload │ CodeViewer │ Dashboard │ Settings │ History      │
├─────────────────────────────────────────────────────────────┤
│                     Django REST API                         │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌─────────────┐ │
│  │  Projects │ │  Reviews   │ │    AI    │ │   Config    │ │
│  │  Service  │ │   Engine   │ │ Gateway  │ │  Service    │ │
│  └─────┬─────┘ └─────┬──────┘ └────┬─────┘ └──────┬──────┘ │
│        │             │              │               │        │
├────────┴─────────────┴──────────────┴───────────────┴────────┤
│                       Core Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │   Zip    │ │   Diff   │ │  Token   │ │    Prompt      │  │
│  │  Parser  │ │Processor │ │ Manager  │ │    Engine      │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Project  │ │ Language │ │  Report  │ │      LLM       │  │
│  │ Detector │ │ Handlers │ │Generator │ │    Adapter     │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                        SQLite                                │
│    projects │ reviews │ issues │ ai_configs │ history       │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈选型

| 层 | 技术 | 选型理由 |
|----|------|---------|
| 前端 | React + Vite + TypeScript | 组件化开发、快速构建、类型安全 |
| 状态管理 | Zustand | 轻量、简单、无样板代码 |
| UI 组件 | Ant Design | 企业级组件库，开箱即用 |
| 代码高亮 | Monaco Editor / Prism.js | 行级别标注、语法高亮 |
| 后端 | Django 5.x + DRF | 成熟的 Python Web 框架、自带 ORM 和 Admin |
| 异步任务 | Django Celery + Redis | 处理长时间运行的 AI 审查任务 |
| AI 接入 | LiteLLM | 统一 20+ LLM 提供商的 API 接口 |
| 数据库 | SQLite | 零配置本地部署，无需额外安装 |
| 文件存储 | 本地文件系统 | 压缩包解压后的源码文件 |

---

## 2. 后端架构

### 2.1 Django 应用结构

```
backend/
├── config/                        # Django 项目配置
│   ├── settings.py                # 全局设置
│   ├── urls.py                    # 根路由
│   ├── celery.py                  # Celery 异步任务配置
│   └── wsgi.py
│
├── apps/
│   ├── projects/                  # 项目管理模块
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── services/
│   │       ├── zip_parser.py         # 压缩包解析服务
│   │       ├── project_detector.py   # 项目类型检测服务
│   │       └── file_filter.py        # 文件过滤服务
│   │
│   ├── reviews/                   # 代码审查模块
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tasks.py                  # Celery 异步审查任务
│   │   └── services/
│   │       ├── review_engine.py      # 审查调度器（核心）
│   │       ├── chunk_manager.py      # 代码分片管理
│   │       ├── result_aggregator.py  # 结果聚合器
│   │       ├── report_generator.py   # 报告生成器
│   │       └── severity_classifier.py
│   │
│   ├── ai/                        # AI 集成模块
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── services/
│   │       ├── llm_adapter.py        # LLM 统一适配器
│   │       ├── prompt_engine.py      # Prompt 模板引擎
│   │       ├── response_parser.py    # AI 输出解析器
│   │       └── token_manager.py      # Token 预算管理
│   │   └── prompts/                  # Prompt 模板目录
│   │       ├── system_base.txt
│   │       ├── system_security.txt
│   │       ├── user_review.txt
│   │       ├── output_schema.json
│   │       └── languages/            # 语言专项 Prompt
│   │           ├── python.txt
│   │           ├── typescript.txt
│   │           ├── go.txt
│   │           └── ...
│   │
│   └── common/                    # 公共模块
│       ├── models.py              # 基础模型（TimestampMixin 等）
│       ├── pagination.py          # 分页器
│       └── exceptions.py          # 自定义异常
│
├── manage.py
├── requirements.txt
└── db.sqlite3
```

### 2.2 核心服务职责

#### Projects Service — 项目管理

```
zip_parser.py:
  - 支持格式: .zip, .tar.gz, .tar.bz2
  - 解压到 MEDIA_ROOT/uploads/{project_id}/
  - 安全检查: 路径穿越防护、文件大小校验
  - 排除规则: node_modules/, .git/, venv/, __pycache__/, dist/

project_detector.py:
  - 扫描配置文件识别项目类型
  - 映射规则:
      package.json      → Node.js/TypeScript
      pyproject.toml    → Python
      go.mod            → Go
      Cargo.toml        → Rust
      pom.xml           → Java/Maven
      build.gradle      → Java/Gradle
      *.sln             → C#/.NET
      CMakeLists.txt    → C/C++
  - 统计语言分布（按文件扩展名和代码行数加权）

file_filter.py:
  - 过滤二进制文件（图片、字体、编译产物）
  - 过滤第三方代码（vendor/, third_party/）
  - 过滤生成代码（.generated., dist/, build/）
  - 识别可审查的源码文件列表
```

#### Reviews Service — 审查引擎

```
review_engine.py (核心调度器):
  - 8 阶段流水线:
    1. 项目指纹识别 → detect_project()
    2. 文件分类过滤 → filter_files()
    3. Token 预算评估 → calculate_budget()
    4. 代码分片 → create_chunks()
    5. AI 审查执行 → execute_review()
    6. 结果聚合 → aggregate_results()
    7. 报告生成 → generate_report()
    8. 持久化 → save_review()

chunk_manager.py:
  - 三级策略（借鉴 PR-Agent）:
    Level 1 (小项目): 全量审查，所有文件放入单个 Prompt
    Level 2 (中项目): 按模块分组，每组独立审查
    Level 3 (大项目): 按文件分片，先审查核心文件，再审查外围

result_aggregator.py:
  - 去重: 相同文件相同行范围的问题合并
  - 分类: 按严重性和维度分组
  - 摘要: 调用 AI 生成总体评估

report_generator.py:
  - Markdown 格式报告
  - PDF 导出（可选）
  - 结构化 JSON（供前端消费）
```

#### AI Service — AI 集成层

```
llm_adapter.py:
  - 基于 LiteLLM 的统一适配器
  - 支持:
      OpenAI: GPT-4o, GPT-5, o3, o4-mini
      Anthropic: Claude Sonnet 4.6, Claude Opus 4.7
      Google: Gemini Pro, Gemini Flash
      DeepSeek: DeepSeek-V3, DeepSeek-Coder
      Ollama: 本地模型（Qwen, Llama, Mistral 等）
      OpenRouter: 多模型路由
  - 用户自带 API Key，系统不代理计费
  - 内置重试和降级策略

prompt_engine.py:
  - Jinja2 模板渲染
  - 动态组装: 基础 Prompt + 语言专项 + 用户自定义指令
  - 变量注入: 项目上下文、文件列表、代码内容

response_parser.py:
  - 多层容错解析（借鉴 PR-Agent 的 load_yaml）
  - 支持 JSON/YAML/Markdown 格式输出
  - 自动修复常见 AI 输出格式错误

token_manager.py:
  - 基于 tiktoken 的 Token 计算
  - 根据模型上下文窗口动态调整
  - 预留 system prompt + output format 的 Token 空间
```

---

## 3. 数据模型设计

### 3.1 ER 关系图

```
Project 1──1 ProjectStats
Project 1──N ProjectFile
Project 1──N Review
Review   1──N ReviewIssue
AIConfig (独立配置表)
```

### 3.2 表结构

#### projects_project

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| name | VARCHAR(255) | 项目名称 |
| upload_file | FilePath | 上传文件路径 |
| status | VARCHAR(20) | uploading / parsing / ready / error |
| project_type | VARCHAR(50) | nodejs / python / go / rust / java / unknown |
| detected_languages | JSON | `{"python": 60, "typescript": 30}` |
| detected_frameworks | JSON | `["Django", "React"]` |
| total_files | INT | 文件总数 |
| total_lines | INT | 代码行总数 |
| file_path | VARCHAR(512) | 解压后的根目录路径 |
| created_at | DATETIME | 创建时间 |

#### projects_projectfile

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| project | FK(Project) | 所属项目 |
| file_path | VARCHAR(1024) | 相对文件路径 |
| language | VARCHAR(30) | 编程语言 |
| line_count | INT | 代码行数 |
| content | TEXT | 文件内容 |
| is_vendor | BOOLEAN | 是否第三方代码 |
| is_generated | BOOLEAN | 是否生成代码 |

#### projects_projectstats

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| project | FK(Project, OneToOne) | 所属项目 |
| language_distribution | JSON | 语言分布统计 |
| dependency_list | JSON | 依赖列表 |
| framework_detected | VARCHAR(100) | 检测到的框架 |
| code_lines | INT | 有效代码行 |
| comment_lines | INT | 注释行 |
| blank_lines | INT | 空行 |

#### reviews_review

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| project | FK(Project) | 审查的项目 |
| status | VARCHAR(20) | pending / running / completed / failed |
| ai_model | VARCHAR(100) | 使用的 AI 模型 |
| ai_provider | VARCHAR(50) | AI 提供商 |
| progress | INT | 审查进度 0-100 |
| total_issues | INT | 问题总数 |
| critical_count | INT | CRITICAL 级别数 |
| high_count | INT | HIGH 级别数 |
| medium_count | INT | MEDIUM 级别数 |
| low_count | INT | LOW 级别数 |
| summary | TEXT | AI 总体评估 |
| error_message | TEXT | 失败原因（如有） |
| started_at | DATETIME | 开始时间 |
| completed_at | DATETIME | 完成时间 |
| created_at | DATETIME | 创建时间 |

#### reviews_reviewissue

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| review | FK(Review) | 所属审查 |
| file_path | VARCHAR(1024) | 文件路径 |
| start_line | INT | 起始行号 |
| end_line | INT | 结束行号 |
| severity | VARCHAR(20) | critical / high / medium / low |
| dimension | VARCHAR(30) | security / correctness / performance / ... |
| title | VARCHAR(500) | 问题标题 |
| description | TEXT | 问题描述 |
| suggestion | TEXT | 修复建议 |
| code_snippet | TEXT | 问题代码片段 |
| fix_snippet | TEXT | 建议修复代码 |

#### ai_aiconfig

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| provider | VARCHAR(50) | openai / anthropic / google / deepseek / ollama |
| display_name | VARCHAR(100) | 显示名称 |
| api_key | VARCHAR(500) | 加密存储的 API Key |
| model_name | VARCHAR(100) | 模型名称 |
| base_url | VARCHAR(500) | 自定义 API 端点（Ollama 等） |
| is_default | BOOLEAN | 是否默认配置 |
| extra_settings | JSON | `{"temperature": 0.3, "max_tokens": 4096}` |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## 4. API 设计

### 4.1 端点列表

```
# === 项目管理 ===
POST   /api/projects/upload/              上传压缩包，创建项目
GET    /api/projects/                      项目列表（分页）
GET    /api/projects/{id}/                 项目详情
GET    /api/projects/{id}/files/           文件树（树形结构）
GET    /api/projects/{id}/files/{path}/    文件内容
GET    /api/projects/{id}/stats/           项目统计
DELETE /api/projects/{id}/                 删除项目

# === 代码审查 ===
POST   /api/projects/{id}/reviews/         发起审查
GET    /api/reviews/                       审查列表（分页）
GET    /api/reviews/{id}/                  审查详情 + 摘要
GET    /api/reviews/{id}/issues/           问题列表（支持筛选参数）
GET    /api/reviews/{id}/report/           导出报告 (?format=markdown|pdf)

# === AI 配置 ===
GET    /api/ai/configs/                    获取所有配置
POST   /api/ai/configs/                    添加配置
PUT    /api/ai/configs/{id}/               更新配置
DELETE /api/ai/configs/{id}/               删除配置
POST   /api/ai/configs/{id}/test/          测试连接
GET    /api/ai/models/                     可用模型列表

# === 系统 ===
GET    /api/system/status/                 系统状态
```

### 4.2 关键 API 请求/响应示例

**POST /api/projects/upload/**

```json
// Request: multipart/form-data
{
  "file": "<binary>",
  "name": "my-project"
}

// Response: 201 Created
{
  "id": "uuid",
  "name": "my-project",
  "status": "parsing",
  "message": "项目上传成功，正在解析中..."
}
```

**POST /api/projects/{id}/reviews/**

```json
// Request
{
  "ai_config_id": "uuid",          // 可选，默认使用默认配置
  "custom_instructions": "...",    // 可选，自定义审查指令
  "focus_files": ["src/app.ts"]    // 可选，指定重点审查文件
}

// Response: 202 Accepted
{
  "id": "uuid",
  "status": "pending",
  "message": "审查任务已提交"
}
```

**GET /api/reviews/{id}/issues/?severity=high&dimension=security**

```json
{
  "count": 12,
  "results": [
    {
      "id": "uuid",
      "file_path": "src/auth/login.py",
      "start_line": 45,
      "end_line": 48,
      "severity": "high",
      "dimension": "security",
      "title": "SQL 注入风险",
      "description": "使用字符串拼接构建 SQL 查询",
      "suggestion": "使用参数化查询替代字符串拼接",
      "code_snippet": "query = f\"SELECT * FROM users WHERE name='{name}'\"",
      "fix_snippet": "query = \"SELECT * FROM users WHERE name=%s\""
    }
  ]
}
```

---

## 5. 核心流程设计

### 5.1 审查引擎流水线

```
用户上传压缩包
       │
       ▼
  ┌─────────────┐
  │ Phase 1     │  ZipParser: 解压 → 安全检查 → 文件扫描
  │ 项目解析    │  ProjectDetector: 识别语言/框架/依赖
  │             │  FileFilter: 过滤可审查文件
  └─────┬───────┘
        │ 返回 Project + ProjectFile 列表
        ▼
  ┌─────────────┐
  │ Phase 2     │  TokenManager: 计算 token 总量
  │ 审查准备    │  ChunkManager: 根据预算决定分片策略
  │             │  PromptEngine: 组装 System + User Prompt
  └─────┬───────┘
        │ 返回 Chunk 列表 + Prompt 模板
        ▼
  ┌─────────────┐
  │ Phase 3     │  LLMAdapter: 调用 AI 模型审查每个 Chunk
  │ AI 审查     │  ResponseParser: 解析 AI 输出为结构化数据
  │             │  （可并行处理多个 Chunk）
  └─────┬───────┘
        │ 返回 Issue 列表
        ▼
  ┌─────────────┐
  │ Phase 4     │  ResultAggregator: 去重、合并、分类
  │ 结果处理    │  SeverityClassifier: 校验严重性分类
  │             │  ReportGenerator: 生成报告
  └─────┬───────┘
        │ 返回 Review + ReviewIssue 列表
        ▼
  ┌─────────────┐
  │ Phase 5     │  持久化到 SQLite
  │ 存储 & 通知 │  前端通过轮询/SSE 获取进度和结果
  └─────────────┘
```

### 5.2 Token 预算管理策略

借鉴 PR-Agent 的三级策略：

```
输入: target_files[], model_context_window

total_tokens = sum(file.token_count for file in target_files)

if total_tokens < context_window * 0.5:
    → Level 1: 全量审查
      所有文件放入单个 Prompt，一次 AI 调用

elif total_tokens < context_window * 2:
    → Level 2: 分组审查
      按语言/模块分组，每组一次 AI 调用
      核心文件优先

else:
    → Level 3: 分片审查
      按文件优先级排序，每 N 个 token 一片
      先审查核心入口文件，再审查工具/配置
      最终额外调用 AI 汇总整体评估
```

### 5.3 Prompt 模板架构

借鉴 PR-Agent 的 System/User 分离 + ECC 的多语言 Agent 委托：

```
System Prompt 组装:
  base_system.txt                    # 基础角色定义 + 输出格式
  + languages/{lang}.txt             # 语言专项规则（动态注入）
  + extra_instructions.txt           # 用户自定义指令（可选）

User Prompt 组装:
  project_context                    # 项目类型、语言分布、框架
  + file_list_with_stats             # 文件列表和代码统计
  + code_content_with_line_numbers   # 代码内容（带行号标注）
  + output_format_reminder           # 输出格式提示
```

**输出格式定义（JSON Schema）：**

```json
{
  "issues": [
    {
      "file": "src/auth/login.py",
      "start_line": 45,
      "end_line": 48,
      "severity": "high",
      "dimension": "security",
      "title": "SQL 注入风险",
      "description": "使用字符串拼接构建 SQL 查询...",
      "suggestion": "使用参数化查询...",
      "code_snippet": "...",
      "fix_snippet": "..."
    }
  ],
  "summary": {
    "overall_assessment": "...",
    "key_findings": ["...", "..."],
    "estimated_risk_level": "high"
  }
}
```

---

## 6. 前端架构

### 6.1 页面结构

```
/                    → Upload（首页，上传入口）
/projects/:id        → ProjectOverview（项目概览 + 发起审查）
/reviews/:id         → ReviewDashboard（审查结果仪表盘）
/reviews/:id/code    → CodeViewer（代码查看器 + 行标注）
/settings            → Settings（AI 配置管理）
/history             → History（审查历史）
```

### 6.2 状态管理（Zustand）

```
projectStore:
  - currentProject: Project | null
  - fileList: TreeNode[]
  - uploadFile(file) → async
  - fetchProject(id) → async

reviewStore:
  - currentReview: Review | null
  - issues: ReviewIssue[]
  - filters: { severity, dimension, file_path, keyword }
  - startReview(projectId, config) → async
  - fetchReview(id) → async
  - fetchIssues(reviewId, filters) → async

configStore:
  - aiConfigs: AIConfig[]
  - defaultConfig: AIConfig | null
  - fetchConfigs() → async
  - saveConfig(config) → async
  - testConnection(configId) → async
```

### 6.3 核心组件

| 组件 | 职责 |
|------|------|
| FileTree | 递归渲染文件树，点击文件切换代码视图 |
| CodeViewer | Monaco Editor 只读模式，行级别标注问题 |
| IssueCard | 展示单个问题详情（严重性、描述、建议、代码对比） |
| SeverityBadge | 严重性标签（CRITICAL/HIGH/MEDIUM/LOW） |
| ReviewProgress | 审查进度条 + 当前阶段描述 |
| FilterPanel | 多维度筛选面板 |
| StatsChart | 严重性分布图、维度热力图 |
| LanguageChart | 语言分布饼图 |

---

## 7. 安全设计

### 7.1 上传安全

- 文件大小限制: 100MB
- 解压炸弹防护: 限制解压后总大小（1GB）和文件数量（10000）
- 路径穿越防护: 校验解压路径不包含 `..`
- 文件类型白名单: 仅接受 `.zip`, `.tar.gz`, `.tar.bz2`

### 7.2 API Key 存储

- 使用 Django 的 `SECRET_KEY` 加密存储 API Key
- API Key 不在前端明文展示，仅显示最后 4 位
- 提供 API Key 删除和轮换功能

### 7.3 代码隔离

- 上传的代码存储在独立目录，不与 Django 应用代码混合
- 定期清理过期项目文件（可配置保留时长）
