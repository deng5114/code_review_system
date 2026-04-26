# Phase 2 Step 6: 性能优化

## 目标

优化前端构建和运行时性能，通过代码分割和分包策略减少首屏加载时间。

## 当前状态

- `App.tsx` 使用标准静态 import 导入所有页面组件
- `vite.config.ts` 无分包配置，所有依赖打包为单 bundle
- 页面组件：Upload(104行)、ProjectOverview(139行)、Settings(201行)、CodeViewer(236行)、ReviewDashboard(248行)

## 实施步骤

### 1. 路由级代码分割

**文件**: `frontend/src/App.tsx`

- 将 5 个页面组件改为 `React.lazy()` 动态导入
- Layout 组件保持静态导入（始终渲染，无需延迟加载）
- 添加 `<Suspense>` 包装路由，提供加载回退 UI
- 使用 Ant Design 的 `Spin` 组件作为加载指示器

### 2. Vite 手动 chunk 分割

**文件**: `frontend/vite.config.ts`

分包策略：
- `react-vendor`: react, react-dom, react-router-dom
- `antd-vendor`: antd, @ant-design/icons
- `monaco-vendor`: monaco-editor, @monaco-editor/react
- `echarts-vendor`: echarts, echarts-for-react
- `vendor`: 其他第三方依赖（axios, zustand）

### 3. 构建优化配置

- 设置 chunk 大小警告阈值为 1000KB
- 配置 CSS 代码分割
- 配置资源文件名 hash 策略（缓存优化）

### 4. 验证

- 执行 `pnpm build` 验证构建成功
- 检查各 chunk 文件大小
- 确认首屏不加载 Monaco/ECharts（最大的两个依赖）

## 验收标准

- [ ] 首屏加载 < 2 秒
- [ ] 主 bundle < 500KB
- [ ] 路由切换流畅（无白屏闪烁）
- [ ] 各 vendor chunk 合理分离
- [ ] 构建无错误、无警告
