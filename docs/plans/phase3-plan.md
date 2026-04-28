# Phase 3 实现计划：用户系统、首页、PDF 导出

> **阶段目标**: 从单用户工具升级为多用户平台
> **前置阶段**: Phase 2 — 功能增强与质量加固 (已完成)
> **预计复杂度**: HIGH

---

## 需求重述

1. **首页与上传页分离** — 当前 `/` 和 `/upload` 都指向同一个上传页面，需要将首页改为审查记录列表页
2. **首页功能** — 用户可以查看自己的历史审查记录，包括项目名称、审查状态、时间等
3. **用户注册/登录** — 完整的认证系统，支持注册、登录、登出
4. **PDF 导出审查报告** — 在审查完成页面支持 PDF 格式导出
5. **审查记录持久化** — 审查记录按用户隔离存储，已由 SQLite 持久化，需加上用户维度

---

## 实现步骤

### Step 3.1 — 后端用户认证系统

**优先级**: HIGH (其他所有功能依赖此步)

**后端变更**:

1. 创建 `apps/users` Django app
   - `models.py` — 自定义 User 模型（继承 `AbstractUser`，添加 avatar/phone 等扩展字段）
   - `serializers.py` — 注册、登录、用户信息序列化器
   - `views.py` — 注册、登录、登出、用户信息 API
   - `urls.py` — 认证相关路由

2. 认证方案：**JWT (SimpleJWT)** ✅ 已确认
   - Access Token + Refresh Token
   - Access Token 有效期 2 小时，Refresh Token 7 天
   - 前端存储在 localStorage，请求头 `Authorization: Bearer <token>`
   - 注册无需邮箱验证，直接注册 ✅

3. 数据库迁移
   - Project 模型添加 `owner` FK → User
   - Review 模型通过 Project 间接关联 User
   - AIConfig 模型添加 `owner` FK → User
   - 创建迁移文件，为现有数据设置默认 owner（匿名用户或第一个注册用户）

4. API 权限保护
   - 所有 ViewSet 添加 `IsAuthenticated` 权限
   - 数据查询按用户过滤（`request.user`）
   - 注册和登录接口允许匿名访问

**新增依赖**: `djangorestframework-simplejwt>=5.3`

**关键文件**:
- `backend/apps/users/` — 新建 app
- `backend/config/settings.py` — 配置 JWT、AUTH_USER_MODEL
- `backend/config/urls.py` — 注册 users app 路由
- `backend/apps/projects/models.py` — 添加 owner 字段
- `backend/apps/ai/models.py` — 添加 owner 字段
- `backend/apps/projects/views.py` — 添加权限和数据过滤
- `backend/apps/reviews/views.py` — 添加权限和数据过滤
- `backend/apps/ai/views.py` — 添加权限和数据过滤

---

### Step 3.2 — 前端认证系统

**优先级**: HIGH (依赖 Step 3.1)

**前端变更**:

1. 创建认证相关组件
   - `pages/Login.tsx` — 登录页面
   - `pages/Register.tsx` — 注册页面
   - `stores/authStore.ts` — 认证状态管理（token、用户信息、登录/登出操作）
   - `api/auth.ts` — 认证 API 调用
   - `components/ProtectedRoute.tsx` — 路由守卫

2. API 客户端改造
   - Axios 拦截器自动附加 JWT token
   - 401 响应自动跳转登录页
   - Token 过期自动刷新

3. 路由调整
   - 添加 `/login` 和 `/register` 路由（不使用 AppLayout）
   - 所有功能路由用 `ProtectedRoute` 包裹
   - 已登录用户访问登录/注册页自动跳转首页

4. 导航栏更新
   - 显示当前用户信息
   - 添加登出按钮
   - 未登录显示登录/注册入口

**关键文件**:
- `frontend/src/pages/Login.tsx` — 新建
- `frontend/src/pages/Register.tsx` — 新建
- `frontend/src/stores/authStore.ts` — 新建
- `frontend/src/api/auth.ts` — 新建
- `frontend/src/components/ProtectedRoute.tsx` — 新建
- `frontend/src/api/client.ts` — 修改（添加拦截器）
- `frontend/src/App.tsx` — 修改（添加认证路由和守卫）
- `frontend/src/components/Layout.tsx` — 修改（添加用户信息）

---

### Step 3.3 — 首页（审查记录列表）

**优先级**: HIGH (依赖 Step 3.2)

**前端变更**:

1. 创建首页组件 `pages/Home.tsx`
   - 审查记录列表（表格展示）
   - 每条记录显示：项目名称、审查状态、问题数量、AI 模型、创建时间
   - 支持状态筛选、关键词搜索、分页
   - 点击记录跳转到对应的 ReviewDashboard

2. 路由调整
   - `/` → `Home` (审查记录首页)
   - `/upload` → `Upload` (上传页面，独立入口)
   - 删除 `/upload` 对 Upload 的重复映射（只保留 `/upload`）

3. 后端 API 优化
   - 审查列表 API 返回关联的项目信息（项目名称、文件数）
   - 支持按状态、时间范围筛选
   - 支持分页

**关键文件**:
- `frontend/src/pages/Home.tsx` — 新建
- `frontend/src/App.tsx` — 修改路由
- `frontend/src/components/Layout.tsx` — 修改菜单
- `frontend/src/stores/reviewStore.ts` — 添加列表加载方法
- `frontend/src/api/reviews.ts` — 添加列表查询 API
- `backend/apps/reviews/views.py` — 优化列表查询
- `backend/apps/reviews/serializers.py` — 列表序列化器包含项目信息

---

### Step 3.4 — PDF 导出审查报告

**优先级**: MEDIUM (依赖 Step 3.2)

**方案选择**:

后端生成 PDF 方案（推荐）：
- 使用 `weasyprint` 或 `reportlab` 在后端生成 PDF
- 后端渲染 HTML 模板 → 转换为 PDF
- 前端通过 `/api/reviews/{id}/report/pdf/` 下载

前端生成 PDF 方案：
- 使用 `html2canvas` + `jspdf` 在前端生成
- 优点：无需后端依赖
- 缺点：质量较差，中文支持不稳定

**确定方案**：**reportlab** ✅ 已确认
- 纯 Python，无系统依赖（Windows 友好）
- 手动排版，灵活度高
- 中文支持好（注册 TTF 字体）

1. 后端创建 PDF 生成服务
   - 使用 reportlab 生成 PDF
   - 注册中文字体（SimHei/微软雅黑）
   - API 端点：`GET /api/reviews/{id}/report/pdf/`

2. 前端添加导出按钮
   - ReviewDashboard 页面添加"导出 PDF"按钮
   - 下载后端生成的 PDF 文件

**新增依赖**: `reportlab>=4.0`

**关键文件**:
- `backend/apps/reviews/services/pdf_generator.py` — 新建
- `backend/apps/reviews/views.py` — 添加 PDF 导出端点
- `backend/apps/reviews/urls.py` — 添加路由
- `frontend/src/pages/ReviewDashboard.tsx` — 添加导出按钮

---

## 依赖关系

```
Step 3.1 (后端认证) → Step 3.2 (前端认证) → Step 3.3 (首页)
                                         → Step 3.4 (PDF 导出)
```

- Step 3.1 和 3.2 是顺序依赖，必须先完成
- Step 3.3 和 3.4 在 3.2 完成后可以并行开发
- 所有步骤都需要修改路由和导航，注意协调

---

## 风险评估

| 风险 | 严重程度 | 缓解措施 |
|------|---------|---------|
| JWT token 在 WebSocket 中传递 | MEDIUM | WebSocket 连接时通过 URL query param 或首次消息传递 token |
| 现有数据迁移（添加 owner） | MEDIUM | 创建数据迁移，设置默认 owner |
| reportlab 中文字体 | LOW | Windows 系统自带中文字体，可直接使用 |
| PDF 中文渲染 | MEDIUM | 确保模板使用支持中文的字体 |
| Token 刷新竞态 | LOW | 使用互斥锁防止并发刷新 |

---

## 预计工作量

| Step | 后端 | 前端 | 测试 | 总计 |
|------|------|------|------|------|
| 3.1 用户认证 | 2-3h | — | 1h | 3-4h |
| 3.2 前端认证 | — | 2-3h | 1h | 3-4h |
| 3.3 首页 | 0.5h | 2-3h | 0.5h | 3-4h |
| 3.4 PDF 导出 | 2-3h | 0.5h | 0.5h | 3-4h |
| **总计** | **4-6.5h** | **4.5-6.5h** | **3h** | **12-16h** |

---

## 已确认决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 认证方案 | JWT (SimpleJWT) | 无状态，适合前后端分离 |
| PDF 生成 | reportlab | 纯 Python，Windows 友好，中文支持好 |
| 邮箱验证 | 不需要 | 简化开发，适合内部工具/演示 |
