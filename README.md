# CodeReview Pro

基于 AI 的智能代码审查系统。上传代码压缩包，自动解析项目结构，调用大语言模型进行多维度审查，生成带有行级问题标注的结构化审查报告。

## 功能特性

- **项目上传与解析** — 支持 zip/tar.gz/tar.bz2，自动检测项目类型和语言分布，过滤依赖目录和二进制文件
- **AI 多维度审查** — 7 个审查维度（安全性、正确性、性能、可维护性、类型安全、完整性、最佳实践），4 级严重性（critical/high/medium/low）
- **多模型支持** — 通过 LiteLLM 接入 OpenAI、Anthropic、Google、DeepSeek、Ollama、OpenRouter 等，支持 fallback 链
- **实时进度** — WebSocket 推送审查进度
- **代码查看器** — Monaco Editor 内联问题高亮，点击 issue 自动跳转到对应文件和行号
- **可视化报告** — 严重性分布柱状图 + 7 维雷达图，支持导出 Markdown 报告

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Django 5 + DRF + Celery + Channels |
| 前端 | React 19 + TypeScript + Vite 8 + Ant Design |
| 编辑器 | Monaco Editor |
| 图表 | ECharts |
| 状态管理 | Zustand |
| AI 接入 | LiteLLM（多供应商统一适配） |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |

## 项目结构

```
code_review_system/
├── backend/                    # Django 后端
│   ├── apps/
│   │   ├── projects/           # 项目上传、解析、文件管理
│   │   ├── reviews/            # 审查引擎、任务调度、报告生成
│   │   ├── ai/                 # LLM 适配、提示词引擎、响应解析
│   │   └── common/             # 基础模型、分页、异常处理
│   ├── config/                 # Django 配置（settings、celery、asgi）
│   └── requirements.txt
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/              # 5 个页面（上传、项目概览、审查仪表盘、代码查看器、设置）
│   │   ├── stores/             # Zustand 状态（project、review、config）
│   │   ├── api/                # Axios API 层
│   │   ├── components/         # 布局、筛选面板、图表、ErrorBoundary
│   │   └── utils/              # 文件树构建、常量
│   ├── e2e/                    # Playwright E2E 测试
│   └── package.json
└── docs/                       # 架构文档、需求规格、实现计划、阶段报告
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- pnpm

### 后端启动

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

开发模式默认使用 Celery eager 执行 + InMemoryChannelLayer，**无需 Redis**。

### 前端启动

```bash
cd frontend
pnpm install
pnpm dev
```

访问 http://localhost:5173，前端会代理 `/api` 和 `/media` 到后端。

### AI 模型配置

1. 启动后访问 **设置页面**（http://localhost:5173/settings）
2. 添加 AI 配置：选择供应商、填入 API Key、选择模型
3. 点击"测试连接"验证可用性
4. 设为默认配置后即可开始审查

## 页面说明

| 页面 | 路径 | 功能 |
|------|------|------|
| 上传 | `/upload` | 上传代码压缩包 |
| 项目概览 | `/projects/:id` | 查看项目结构、语言分布、触发审查 |
| 审查仪表盘 | `/reviews/:id` | 审查结果总览、严重性分布、问题列表 |
| 代码查看器 | `/reviews/:id/code` | Monaco 编辑器 + 行级问题标注 |
| 设置 | `/settings` | AI 模型配置管理 |

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/projects/` | POST | 上传并解析项目 |
| `/api/projects/{id}/` | GET/DELETE | 项目详情/删除 |
| `/api/projects/{id}/files/` | GET | 文件列表 |
| `/api/projects/{id}/files/{fid}/` | GET | 文件内容 |
| `/api/reviews/` | POST | 创建审查任务 |
| `/api/reviews/{id}/` | GET | 审查详情 |
| `/api/reviews/{id}/issues/` | GET | 问题列表（支持筛选） |
| `/api/reviews/{id}/report/` | GET | 导出报告（JSON/Markdown） |
| `/api/ai/configs/` | CRUD | AI 配置管理 |
| `/api/ai/configs/test-connection/` | POST | 测试连接 |
| `ws/reviews/{id}/progress/` | WS | 实时审查进度 |

## 测试

```bash
# 后端
cd backend
pytest

# 前端单元测试
cd frontend
pnpm test

# 前端覆盖率
pnpm test:coverage

# E2E 测试
pnpm test:e2e
```

## 生产部署

生产环境需要：

- Redis（Celery broker + Channels layer）
- 设置 `DJANGO_DEVELOPMENT=False`
- 配置 `CELERY_BROKER_URL`、`CHANNEL_LAYERS` 指向 Redis
- 使用 Daphne 或 Gunicorn + Uvicot 作为 ASGI 服务器

## 文档

详细文档位于 `docs/` 目录：

- `architecture.md` — 系统架构、ER 图、审查流水线设计
- `requirements.md` — 产品需求规格
- `implementation-plan.md` — 三阶段实现计划
- `phase-reports/` — 各阶段完成报告
