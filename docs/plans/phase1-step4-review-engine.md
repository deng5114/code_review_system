# Phase 1 Step 4: 审查引擎核心 — 实施计划

## 目标

实现完整的审查流水线，包括 8 阶段调度器、三级分片策略、结果聚合、报告生成和 Celery 异步任务集成。

## 实施步骤（TDD 驱动）

### Phase 1: 基础组件（3 个组件，可并行开发）

#### A. ChunkManager — 分片管理器
- **tests/test_chunk_manager.py** — 先写测试 (RED)
  - 小项目 → 全量策略（总 token < context_window * 0.5）
  - 中项目 → 分组策略（按语言/模块分组）
  - 大项目 → 分片策略（按优先级排序切片）
  - 边界条件：空文件、超大单文件、无 token 预算
- **services/chunk_manager.py** — 实现 (GREEN)
  - `Chunk` dataclass: files, estimated_tokens, group_label
  - `ChunkManager` 类:
    - `plan_chunks(files, model, context_window)` → list[Chunk]
    - `_classify_strategy(total_tokens, context_window)` → strategy
    - `_group_by_language(files)` → dict[str, list]
    - `_group_by_module(files)` → dict[str, list]
    - `_sort_by_priority(files)` → list（入口文件 > 核心逻辑 > 配置工具）

#### B. ResultAggregator — 结果聚合器
- **tests/test_result_aggregator.py** — 先写测试 (RED)
  - 完全重复问题去重
  - 行范围重叠合并
  - 低置信度问题降级
  - 按严重性/维度/文件分组统计
- **services/result_aggregator.py** — 实现 (GREEN)
  - `AggregatedResult` dataclass: issues, stats
  - `ResultAggregator` 类:
    - `aggregate(issues: list[ParsedIssue])` → AggregatedResult
    - `_deduplicate(issues)` → list[ParsedIssue]
    - `_downgrade_low_confidence(issues, threshold=0.5)` → list
    - `compute_stats(issues)` → dict

#### C. ReportGenerator — 报告生成器
- **tests/test_report_generator.py** — 先写测试 (RED)
  - Markdown 格式正确性
  - JSON 结构符合 schema
  - 空问题列表处理
  - 特殊字符转义
- **services/report_generator.py** — 实现 (GREEN)
  - `ReportGenerator` 类:
    - `generate_markdown(review, issues)` → str
    - `generate_json(review, issues)` → dict

### Phase 2: 核心引擎（依赖 Phase 1）

#### D. ReviewEngine — 核心调度器
- **tests/test_review_engine.py** — 先写测试 (RED)
  - 端到端小项目审查流程（mock LLM）
  - 分片审查流程（mock LLM + 多 chunk）
  - 各阶段失败处理
  - 进度更新正确性
- **services/review_engine.py** — 实现 (GREEN)
  - `ReviewEngine` 类，8 阶段流水线:
    1. 加载项目文件
    2. 过滤不可审查文件
    3. 计算 token 预算
    4. 代码分片（调用 ChunkManager）
    5. AI 审查每个 chunk（调用 LLMAdapter + PromptEngine）
    6. 解析响应（调用 ResponseParser）
    7. 聚合去重（调用 ResultAggregator）
    8. 持久化（保存 ReviewIssue + 更新 Review 状态）

#### E. Celery Tasks — 异步任务
- **tests/test_tasks.py** — 先写测试 (RED)
  - 任务成功执行
  - AI 调用失败处理
  - 状态正确更新
- **tasks.py** — 实现 (GREEN)
  - `start_review_task(review_id)`: 异步启动审查
  - 状态管理: pending → reviewing → completed/failed
  - 时间记录: started_at, completed_at, duration_seconds

### Phase 3: API 层（依赖 Phase 2）

#### F. Serializers + Views + URLs
- **tests/test_views.py** — 先写测试 (RED)
  - POST 创建审查任务
  - GET 审查列表
  - GET 审查详情
  - GET 问题列表（带筛选）
  - GET 报告导出
- **serializers.py** — ReviewSerializer, ReviewIssueSerializer, CreateReviewSerializer
- **views.py** — API 视图
- **urls.py** — 路由更新

## 新建/修改文件清单

```
backend/apps/reviews/
├── services/
│   ├── __init__.py          (新建)
│   ├── chunk_manager.py     (新建)
│   ├── result_aggregator.py (新建)
│   ├── report_generator.py  (新建)
│   └── review_engine.py     (新建)
├── tasks.py                 (新建)
├── serializers.py           (新建)
├── views.py                 (修改)
├── urls.py                  (修改)
└── tests/
    ├── __init__.py          (新建)
    ├── conftest.py          (新建)
    ├── test_chunk_manager.py    (新建)
    ├── test_result_aggregator.py (新建)
    ├── test_report_generator.py  (新建)
    ├── test_review_engine.py     (新建)
    ├── test_tasks.py             (新建)
    └── test_views.py             (新建)
```

## 依赖顺序

```
Phase 1（可并行）:
  A: ChunkManager ──┐
  B: ResultAggregator ──┤
  C: ReportGenerator ──┘
                      ↓
Phase 2（串行）:
  D: ReviewEngine（依赖 A + B）
  E: Tasks（依赖 D）
                      ↓
Phase 3:
  F: Serializers + Views + URLs（依赖 E）
```

## 风险识别

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| Token 计算偏差导致分片不准 | MEDIUM | 预留 20% buffer |
| Celery 配置复杂 | MEDIUM | 开发模式用 task_always_eager=True |
| 大项目审查耗时 | LOW | 分片 + 进度追踪 |
| 并发审查同一项目 | LOW | Review 模型乐观锁 |

## 验收标准

1. 上传一个小型 Python 项目 → 发起审查 → 返回结构化审查结果
2. 问题去重逻辑正确
3. Celery 异步任务正确更新状态
4. API 接口格式统一
5. 测试覆盖率 >= 80%
