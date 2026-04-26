# Phase 2 Step 4: 实时性提升 — WebSocket 进度推送

> 版本: 1.0 | 日期: 2026-04-26
> 状态: 待确认

---

## 目标

使用 Django Channels + WebSocket 替代 3 秒轮询，实现审查进度实时推送。
连接失败时自动降级到轮询机制。

---

## 架构设计

```
Celery Task (on_progress)
  → async_to_sync(channel_layer.group_send)()
    → Redis Channel Layer
      → ReviewProgressConsumer (WebSocket)
        → Frontend useReviewWebSocket Hook
          → reviewStore.updateReviewProgress()
```

---

## 实施步骤

### Step 1: 后端依赖和配置

**修改文件**: `backend/requirements.txt`
- 添加 `channels[daphne]>=4.0.0`
- 添加 `channels-redis>=4.0.0`

**修改文件**: `backend/config/settings.py`
- INSTALLED_APPS 添加 `daphne`, `channels`
- 添加 `ASGI_APPLICATION = "config.asgi.application"`
- 添加 `CHANNEL_LAYERS` 配置 (Redis backend, 复用 Celery 的 Redis)

### Step 2: ASGI 路由和 WebSocket 路由

**新建文件**: `backend/config/routing.py`
- `websocket_urlpatterns` 定义 WebSocket URL 路由
- 路由: `ws/reviews/<uuid:review_id>/progress/`

**修改文件**: `backend/config/asgi.py`
- 使用 `ProtocolTypeRouter` 分流 HTTP 和 WebSocket
- HTTP 走 Django ASGI, WebSocket 走 `AuthMiddlewareStack + URLRouter`

### Step 3: WebSocket Consumer

**新建文件**: `backend/apps/reviews/consumers.py`
- `ReviewProgressConsumer(AsyncWebsocketConsumer)`
- `connect()`: 验证 review_id 存在, 加入 group `review_progress_{review_id}`
- `disconnect()`: 离开 group
- `review_progress()`: 接收 group 消息, 转发给 WebSocket 客户端
- 消息格式: `{"type": "review_progress", "progress": 0-100, "status": "running", "message": "..."}`

### Step 4: Celery Task 集成 Channel Layer

**修改文件**: `backend/apps/reviews/tasks.py`
- 导入 `channels.layers` 和 `asgiref.sync.async_to_sync`
- 修改 `on_progress` 回调: 调用 `group_send` 推送进度到 WebSocket group
- 在状态变更点也推送消息 (RUNNING, COMPLETED, FAILED)

### Step 5: 后端测试

**新建文件**: `backend/apps/reviews/tests/test_consumers.py`
- 测试 WebSocket 连接/断开
- 测试进度消息推送
- 测试无效 review_id 拒绝连接
- 测试消息格式正确性

### Step 6: 前端 WebSocket Hook

**新建文件**: `frontend/src/hooks/useReviewWebSocket.ts`
- 管理 WebSocket 连接生命周期
- 自动重连 (指数退避, 最多 5 次)
- 解析消息并回调
- 连接状态管理 (connecting/connected/disconnected)
- 组件卸载时关闭连接

### Step 7: 前端 Store 和 Dashboard 集成

**修改文件**: `frontend/src/stores/reviewStore.ts`
- 添加 `webSocketStatus` 状态
- 添加 `updateReviewProgress(reviewId, data)` 方法
- WebSocket 优先, 失败降级到轮询

**修改文件**: `frontend/src/pages/ReviewDashboard.tsx`
- 使用 `useReviewWebSocket` hook
- WebSocket 消息实时更新进度条
- 显示连接状态指示器
- WebSocket 断开时自动降级到轮询

### Step 8: 编写完成报告并提交

---

## 消息协议

### 服务端 → 客户端

```json
{
  "type": "review_progress",
  "progress": 45,
  "status": "running",
  "message": "Reviewing chunk 3/7..."
}
```

```json
{
  "type": "review_progress",
  "progress": 100,
  "status": "completed",
  "message": "Review completed"
}
```

```json
{
  "type": "review_progress",
  "progress": 0,
  "status": "failed",
  "message": "Error: API timeout"
}
```

### 降级策略

前端 `useReviewWebSocket`:
1. 尝试建立 WebSocket 连接
2. 如果 `onerror` 或超时 5 秒未连接 → 标记 `unavailable`
3. Dashboard 检测到 `unavailable` → 启动轮询 (保持现有逻辑)
4. WebSocket 重连成功 → 停止轮询, 切回 WebSocket

---

## 文件变更清单

### 新建文件
| 文件 | 用途 |
|------|------|
| `backend/apps/reviews/consumers.py` | WebSocket Consumer |
| `backend/apps/reviews/tests/test_consumers.py` | Consumer 测试 |
| `backend/config/routing.py` | WebSocket URL 路由 |
| `frontend/src/hooks/useReviewWebSocket.ts` | WebSocket Hook |

### 修改文件
| 文件 | 变更 |
|------|------|
| `backend/requirements.txt` | +channels[daphne], +channels-redis |
| `backend/config/settings.py` | +channels 配置, +ASGI_APPLICATION, +CHANNEL_LAYERS |
| `backend/config/asgi.py` | ProtocolTypeRouter 集成 |
| `backend/apps/reviews/tasks.py` | Channel Layer 进度推送 |
| `frontend/src/stores/reviewStore.ts` | +updateReviewProgress, +webSocketStatus |
| `frontend/src/pages/ReviewDashboard.tsx` | WebSocket 集成, 降级逻辑 |

---

## 验收标准

- [ ] WebSocket 连接正常建立
- [ ] 进度实时推送 (无轮询请求)
- [ ] 连接断开时降级到轮询
- [ ] 组件卸载时连接关闭
- [ ] 后端 Consumer 测试通过
- [ ] 无效 review_id 拒绝连接
