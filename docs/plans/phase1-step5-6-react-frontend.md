# Phase 1 Steps 5-6 — React 前端实施计划

> 版本: 1.0 | 日期: 2026-04-24

## Context

Phase 1 后端（Steps 1-4）已全部完成，包含 209 个测试，96% 覆盖率。但前端（Steps 5-6）尚未开发，`frontend/` 目录不存在。本计划覆盖 Phase 1 剩余的前端开发工作，实现从上传到查看审查结果的完整用户链路。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI 框架 |
| Vite | 5+ | 构建工具（开发端口 5173，CORS 已配置） |
| TypeScript | 5+ | 类型安全 |
| Ant Design | 5+ | UI 组件库 |
| @ant-design/icons | - | 图标 |
| @monaco-editor/react | - | 代码查看器 |
| Zustand | 4+ | 状态管理 |
| Axios | 1.7+ | HTTP 客户端 |
| ECharts | 5+ | 图表 |
| echarts-for-react | - | React ECharts 封装 |
| react-router-dom | 6+ | 路由 |

---

## Step 5: React 前端脚手架 + 上传与概览页

### 5.1 项目脚手架

**创建文件**:
```
frontend/
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── vite-env.d.ts
│   ├── api/
│   │   ├── client.ts              # Axios 实例 + 拦截器
│   │   ├── projects.ts            # 项目 API
│   │   ├── reviews.ts             # 审查 API
│   │   └── config.ts              # AI 配置 API
│   ├── stores/
│   │   ├── projectStore.ts        # 项目状态
│   │   ├── reviewStore.ts         # 审查状态
│   │   └── configStore.ts         # AI 配置状态
│   ├── types/
│   │   └── index.ts               # TypeScript 类型定义
│   ├── components/
│   │   └── Layout.tsx             # 全局布局（侧边栏 + 内容区）
│   ├── pages/
│   │   ├── Upload.tsx             # 上传页
│   │   ├── ProjectOverview.tsx    # 项目概览页
│   │   ├── ReviewDashboard.tsx    # 审查仪表盘（Step 6）
│   │   ├── CodeViewer.tsx         # 代码查看器（Step 6）
│   │   └── Settings.tsx           # AI 配置页
│   └── utils/
│       └── constants.ts           # 常量定义
```

**关键配置**:
- `vite.config.ts`: proxy `/api` → `http://localhost:8000`
- `client.ts`: baseURL = `/api`，响应拦截器提取 `data` 字段，错误处理提取 `error.message`

### 5.2 类型定义 (`types/index.ts`)

根据后端序列化器定义 TypeScript 接口：
- `Project` / `ProjectFile` / `ProjectStats`
- `Review` / `ReviewIssue`
- `AIConfig`
- `ApiResponse<T>` / `PaginatedResponse<T>`
- `TreeNode`（文件树节点）

### 5.3 API 封装 (`api/`)

`client.ts`:
- 创建 Axios 实例，baseURL = `/api`
- 响应拦截器：解包 `response.data`，统一错误处理
- 请求拦截器：暂无认证头

`projects.ts`:
- `uploadProject(name, file)` — POST multipart/form-data
- `fetchProjects(page?)` — GET 列表
- `fetchProject(id)` — GET 详情
- `fetchProjectFiles(projectId)` — GET 文件列表
- `fetchFileContent(projectId, fileId)` — GET 单文件内容
- `deleteProject(id)` — DELETE

`reviews.ts`:
- `createReview(projectId, config?)` — POST
- `fetchReviews(params?)` — GET 列表
- `fetchReview(id)` — GET 详情
- `fetchIssues(reviewId, filters?)` — GET 问题列表
- `fetchReport(reviewId, output?)` — GET 报告

`config.ts`:
- `fetchConfigs()` / `createConfig()` / `updateConfig()` / `deleteConfig()`
- `testConnection(configId | params)` — POST 测试连接

### 5.4 Zustand Stores

`projectStore.ts`:
```typescript
interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  fileList: ProjectFile[]
  uploading: boolean
  loading: boolean
  uploadFile: (name: string, file: File) => Promise<Project>
  fetchProjects: () => Promise<void>
  fetchProject: (id: string) => Promise<void>
  fetchFiles: (projectId: string) => Promise<void>
  deleteProject: (id: string) => Promise<void>
}
```

`reviewStore.ts`:
```typescript
interface ReviewStore {
  reviews: Review[]
  currentReview: Review | null
  issues: ReviewIssue[]
  filters: IssueFilters
  loading: boolean
  creating: boolean
  startReview: (projectId: string, config?) => Promise<Review>
  fetchReview: (id: string) => Promise<void>
  fetchIssues: (reviewId: string, filters?) => Promise<void>
  setFilters: (filters: Partial<IssueFilters>) => void
  pollReviewProgress: (id: string) => void  // 轮询直到完成/失败
}
```

`configStore.ts`:
```typescript
interface ConfigStore {
  configs: AIConfig[]
  defaultConfig: AIConfig | null
  loading: boolean
  fetchConfigs: () => Promise<void>
  saveConfig: (config) => Promise<void>
  deleteConfig: (id: string) => Promise<void>
  testConnection: (id: string) => Promise<TestResult>
}
```

### 5.5 Upload 页面

**功能**:
- 拖拽上传区域（Ant Design Dragger）
- 文件类型限制: .zip / .tar.gz / .tar.bz2
- 文件大小限制: 100MB
- 上传中显示进度条
- 上传成功后跳转到 ProjectOverview 页面
- 项目历史列表（最近上传的项目）

**关键交互**:
- 调用 `projectStore.uploadFile(name, file)`
- 上传成功 → `navigate(/projects/${project.id})`
- 上传失败 → 显示错误提示（message.error）

### 5.6 ProjectOverview 页面

**布局**:
```
┌──────────────────────────────────────────────┐
│ 项目信息卡片（名称、类型、语言、框架、文件数） │
├─────────────┬────────────────────────────────┤
│ 文件树      │ 文件内容预览                    │
│ (可展开)    │ (只读显示选中的文件)            │
│             │                                │
│             │                                │
├─────────────┴────────────────────────────────┤
│ [发起审查] 按钮                               │
└──────────────────────────────────────────────┘
```

**功能**:
- 项目信息展示：类型、语言分布（简单标签）、框架、文件数/行数
- 文件树：使用 Ant Design Tree 组件，点击文件显示内容
- 发起审查按钮 → 弹窗选择 AI 配置 → 调用 `reviewStore.startReview()`
- 审查创建成功 → 跳转到 ReviewDashboard

### 5.7 Settings 页面（AI 配置管理）

**功能**:
- 配置列表：表格显示所有 AI 配置
- 新增配置：弹窗表单（提供商、模型、API Key、端点等）
- 编辑/删除配置
- 测试连接按钮
- 设置默认配置

**提供商选择联动**:
- 选择 Ollama → base_url 必填提示
- 不同提供商显示推荐模型列表

---

## Step 6: 审查结果展示

### 6.1 ReviewDashboard 页面

**布局**:
```
┌──────────────────────────────────────────────┐
│ 审查进度条（pending/running 时显示）           │
├──────────────────────────────────────────────┤
│ 摘要区域                                      │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │
│ │总数  │ │严重  │ │高级  │ │中级  │ ...      │
│ │  42  │ │  3   │ │  8   │ │ 15   │         │
│ └──────┘ └──────┘ └──────┘ └──────┘         │
│ AI 总体评估文本                                │
├─────────────┬────────────────────────────────┤
│ 问题列表    │ 筛选面板                         │
│ (IssueCard) │ 严重性 | 维度 | 文件 | 关键词    │
│             │                                  │
│             │                                  │
└─────────────┴────────────────────────────────┘
```

**功能**:
- 审查状态展示（pending → running → completed/failed）
- 进度条 + 进度百分比
- 完成后显示：问题统计卡片（总数 + 四级严重性计数）
- AI 总体评估摘要
- 问题列表（IssueCard 组件）
- 基础筛选（严重性多选）

### 6.2 CodeViewer 页面

**布局**:
```
┌─────────────┬────────────────────────────────┐
│ 文件树      │ Monaco Editor (只读)            │
│ [问题数标注]│                                 │
│             │ 行标注：问题行背景高亮            │
│             │ 鼠标悬停/点击 → 问题卡片弹出     │
│             │                                 │
├─────────────┴────────────────────────────────┤
│ 问题详情面板（点击行标注后展示）                │
│ 标题 | 描述 | 修复建议 | 代码对比             │
└──────────────────────────────────────────────┘
```

**功能**:
- 文件树：每个文件旁标注问题数量，点击切换代码
- Monaco Editor 只读模式 + 语法高亮
- 行级别问题标注：
  - 问题行范围背景高亮（按严重性着色）
  - 行号旁显示严重性图标
  - 点击标注弹出 IssueCard
- 问题详情面板：问题描述 + 修复建议 + 代码对比

### 6.3 IssueCard 组件

展示单个审查问题：
- 严重性标签（颜色编码）+ 维度标签
- 文件路径:行号
- 问题标题
- 展开后：完整描述、修复建议、代码对比（问题代码 vs 修复代码）

### 6.4 SeverityBadge 组件

颜色方案：
- CRITICAL: 红色 (#ff4d4f)
- HIGH: 橙色 (#fa8c16)
- MEDIUM: 金色 (#fadb14)
- LOW: 蓝色 (#1890ff)

### 6.5 审查进度轮询

- 创建审查后跳转到 ReviewDashboard
- 状态为 `pending` 或 `running` 时，每 3 秒轮询 `GET /api/reviews/{id}/`
- `progress` 更新进度条
- `status` 变为 `completed` 或 `failed` 时停止轮询
- 完成后自动加载问题列表

---

## 实施顺序

### 第一步：脚手架 + 基础设施
1. 创建 Vite + React + TypeScript 项目
2. 安装依赖（antd, zustand, axios, react-router-dom, @ant-design/icons）
3. 配置 vite.config.ts（API proxy）
4. 创建 types/index.ts（所有 TypeScript 类型）
5. 创建 api/client.ts（Axios 实例）
6. 创建 api/projects.ts, api/reviews.ts, api/config.ts
7. 创建 Layout 组件（App.tsx 路由配置）
8. 验证：`pnpm dev` 启动成功，API 代理工作

### 第二步：上传页 + 项目概览页
1. 创建 stores/projectStore.ts, stores/configStore.ts
2. 创建 Upload 页面（拖拽上传 + 项目列表）
3. 创建 ProjectOverview 页面（项目信息 + 文件树 + 发起审查）
4. 创建 Settings 页面（AI 配置 CRUD + 测试连接）
5. 验证：上传 zip → 跳转到概览页 → 看到文件树

### 第三步：审查仪表盘 + 代码查看器
1. 创建 stores/reviewStore.ts
2. 创建 ReviewDashboard 页面（进度 + 统计 + 问题列表）
3. 创建 IssueCard 组件
4. 创建 SeverityBadge 组件
5. 创建 CodeViewer 页面（Monaco Editor + 行标注）
6. 实现进度轮询逻辑
7. 验证：发起审查 → 看到进度 → 完成后查看代码标注

---

## 关键文件参考

| 后端文件 | 前端需要对接的内容 |
|----------|-------------------|
| `backend/apps/projects/views.py` | 上传、文件列表、文件内容 API |
| `backend/apps/reviews/views.py` | 审查 CRUD、问题列表、报告 API |
| `backend/apps/ai/views.py` | AI 配置 CRUD、测试连接 API |
| `backend/apps/projects/serializers.py` | 响应数据结构 |
| `backend/apps/reviews/serializers.py` | 响应数据结构 |
| `backend/apps/ai/serializers.py` | 响应数据结构（注意 masked_api_key） |
| `backend/config/settings.py` | CORS 配置（5173 端口） |

## 风险与注意事项

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| Monaco Editor 包体积大 | LOW | 使用 `@monaco-editor/react` 按需加载 |
| 审查轮询频率过高 | LOW | 3 秒间隔 + completed/failed 自动停止 |
| 大文件树渲染性能 | LOW | Ant Design Tree 内置虚拟滚动 |
| Celery/Redis 未启动时审查无法异步 | MEDIUM | 前端需要处理 failed 状态，显示友好错误 |

## 验证方案

1. **脚手架验证**: `pnpm dev` 启动前端，`python manage.py runserver` 启动后端，访问 `http://localhost:5173` 看到 UI
2. **上传验证**: 拖拽上传一个 Python 项目 zip → 跳转到概览页 → 看到文件树和项目信息
3. **配置验证**: Settings 页面添加 OpenAI API Key → 测试连接成功
4. **审查验证**: 发起审查 → 进度条更新 → 完成后看到问题列表和统计
5. **代码查看验证**: 点击问题 → 跳转到 CodeViewer → 看到行标注和问题卡片
