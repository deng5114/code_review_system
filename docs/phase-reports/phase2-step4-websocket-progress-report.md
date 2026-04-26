# Phase 2 Step 4: 实时性提升 — WebSocket 进度推送

**日期**: 2026-04-26
**状态**: 已完成
**测试**: 269 passed (9 new)
**覆盖率**: 96%

---

## 目标

使用 Django Channels + WebSocket 替代 3 秒轮询，实现审查进度实时推送。
连接失败时自动降级到轮询机制。

---

## 变更概览

### 新建文件

| 文件 | 用途 |
|------|------|
| `backend/apps/reviews/consumers.py` | ReviewProgressConsumer — WebSocket 消费者 |
| `backend/apps/reviews/tests/test_consumers.py` | Consumer + _push_progress 测试 (9 tests) |
| `backend/config/routing.py` | WebSocket URL 路由配置 |
| `backend/conftest.py` | 测试环境 InMemoryChannelLayer 配置 |
| `frontend/src/hooks/useReviewWebSocket.ts` | React WebSocket Hook — 连接管理、重连、降级 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/requirements.txt` | +channels[daphne], +channels-redis |
| `backend/config/settings.py` | +daphne/channels INSTALLED_APPS, +ASGI_APPLICATION, +CHANNEL_LAYERS |
| `backend/config/asgi.py` | ProtocolTypeRouter 集成 HTTP + WebSocket |
| `backend/apps/reviews/tasks.py` | _push_progress() 辅助函数, 4 个推送点 |
| `backend/pytest.ini` | +asyncio_mode=auto |
| `frontend/src/stores/reviewStore.ts` | +updateReviewProgress() 方法 |
| `frontend/src/pages/ReviewDashboard.tsx` | WebSocket 集成 + 降级到轮询 + 连接状态指示器 |

---

## 实现细节

### 后端架构

```
Celery Task (on_progress)
  → async_to_sync(channel_layer.group_send)()
    → Redis Channel Layer (db=1)
      → ReviewProgressConsumer (WebSocket)
        → 前端 useReviewWebSocket Hook
```

### WebSocket Consumer (`consumers.py`)

- `connect()`: 加入 group `review_progress_{review_id}`
- `disconnect()`: 离开 group
- `review_progress()`: 转发 channel layer 消息到 WebSocket 客户端
- 消息格式: `{"type": "review_progress", "progress": 0-100, "status": "...", "message": "..."}`

### Celery Task 集成 (`tasks.py`)

新增 `_push_progress()` 辅助函数，使用 `async_to_sync(channel_layer.group_send)()` 从同步 Celery 任务推送到异步 Channel Layer。

4 个推送点：
1. **Review 开始** — progress=0, status=running
2. **进度更新** — on_progress 回调中每次调用
3. **Review 完成** — progress=100, status=completed
4. **Review 失败** — progress=0, status=failed (含错误信息)

异常安全：`_push_progress()` 捕获所有异常并仅记录警告日志，不影响主流程。

### 前端 WebSocket Hook (`useReviewWebSocket.ts`)

- 自动连接/断开管理
- 指数退避重连 (1s, 2s, 4s, 8s, 16s, 最多 5 次)
- 连接超时检测 (5 秒)
- `unavailable` 状态触发降级
- 组件卸载时清理连接

### Dashboard 降级策略

1. 审查进行中时尝试 WebSocket 连接
2. WebSocket `connected` → 显示「实时」标签，进度通过 WebSocket 更新
3. WebSocket `unavailable` → 自动启动轮询，显示「轮询」标签
4. 审查完成/失败 → WebSocket 自动断开

### 测试环境

- `conftest.py` 全局 fixture 覆盖 `CHANNEL_LAYERS` 为 `InMemoryChannelLayer`
- `pytest.ini` 添加 `asyncio_mode = auto` 支持异步测试
- Consumer 测试直接使用 `ReviewProgressConsumer.as_asgi()` 绕过 Origin 验证

---

## 测试覆盖

### Consumer 测试 (9 tests)

| 类别 | 测试数 | 覆盖场景 |
|------|--------|----------|
| WebSocket 连接 | 2 | 成功连接、无效 ID 连接 |
| 消息接收 | 3 | 进度消息、完成消息、失败消息 |
| 断开行为 | 1 | 断开后不再收到消息 |
| _push_progress | 3 | 正常推送、无 channel layer、异常处理 |

---

## 累计进度

| 指标 | Phase 2 Step 3 | Phase 2 Step 4 | 变化 |
|------|----------------|----------------|------|
| 后端测试 | 260 | 269 | +9 |
| 测试覆盖率 | 96% | 96% | - |
| Python 依赖 | 12 | 14 | +2 (channels, channels-redis) |
| 新文件 | ~16 | +5 | 21 |

---

## 下一步

Phase 2 Step 5: 前端测试 (Vitest + Playwright)
