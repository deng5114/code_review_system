# Phase 2 Step 5: 前端测试 — Vitest 单元测试

> 版本: 1.0 | 日期: 2026-04-26

---

## 目标

为前端添加 Vitest 单元测试覆盖，优先测试业务逻辑层。

---

## 实施步骤

### Step 1: 安装依赖和配置 Vitest

- 安装: vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, jsdom
- 新建 `frontend/vitest.config.ts`
- 新建 `frontend/src/test/setup.ts`

### Step 2: 工具函数测试 (高价值、无依赖)

- `frontend/src/utils/__tests__/fileTree.test.ts` — buildFileTree 逻辑
- `frontend/src/utils/__tests__/constants.test.ts` — 数据完整性校验

### Step 3: API 层测试 (Mock axios)

- `frontend/src/api/__tests__/client.test.ts` — extractData 逻辑
- `frontend/src/api/__tests__/projects.test.ts` — CRUD 函数
- `frontend/src/api/__tests__/reviews.test.ts` — CRUD + downloadReport

### Step 4: Store 测试 (Mock API)

- `frontend/src/stores/__tests__/projectStore.test.ts`
- `frontend/src/stores/__tests__/reviewStore.test.ts`
- `frontend/src/stores/__tests__/configStore.test.ts`

### Step 5: Hook 测试 (Mock WebSocket)

- `frontend/src/hooks/__tests__/useReviewWebSocket.test.ts`

### Step 6: 组件测试

- `frontend/src/components/__tests__/FilterPanel.test.tsx`

### Step 7: 代码审查 + 完成报告 + Git 提交

---

## 验收标准

- [ ] 单元测试覆盖率 > 80% (stores, api, utils, hooks)
- [ ] 所有测试通过
- [ ] 测试运行时间 < 30 秒
