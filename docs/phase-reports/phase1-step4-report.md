# Phase 1 Step 4: Review Engine Core — 完成报告

## 概述

实现完整的代码审查引擎核心，包括文件分片策略、AI 调用编排、结果聚合去重、报告生成、Celery 异步任务和 REST API 端点。

## 实现内容

### 新增文件 (10 个)

| 文件 | 用途 | 行数 |
|------|------|------|
| `services/chunk_manager.py` | 三级分片策略 (full/grouped/chunked) | 85 |
| `services/result_aggregator.py` | 问题去重 + 置信度降级 + 统计 | 50 |
| `services/report_generator.py` | Markdown/JSON 报告生成 | 45 |
| `services/review_engine.py` | 8 阶段审查流水线 | 53 |
| `tasks.py` | Celery 异步任务 + 进度回调 | 64 |
| `serializers.py` | DRF 序列化器 (3 个) | 15 |
| `tests/test_chunk_manager.py` | 分片策略测试 | 78 |
| `tests/test_result_aggregator.py` | 结果聚合测试 | 74 |
| `tests/test_report_generator.py` | 报告生成测试 | 78 |
| `tests/test_review_engine.py` | 引擎集成测试 | 89 |
| `tests/test_tasks.py` | 异步任务测试 | 65 |
| `tests/test_views.py` | API 端点测试 | 102 |

### 修改文件 (2 个)

| 文件 | 变更 |
|------|------|
| `views.py` | 实现完整 ReviewViewSet (CRUD + issues + report) |
| `urls.py` | 注册 ReviewViewSet 路由 |

## 架构设计

### 8 阶段审查流水线

```
Load → Filter → Token Budget → Chunk → AI Review → Parse → Aggregate → Persist
```

### 三级分片策略

| 策略 | 触发条件 | 行为 |
|------|----------|------|
| full | < 0.5 × context_window | 所有文件一个 chunk |
| grouped | < 2 × context_window | 按语言分组 |
| chunked | >= 2 × context_window | 按优先级分块 |

### 问题去重

- Key: `(file_path, title, dimension)`
- 合并策略: 取更宽行范围 + 更高严重等级
- 置信度 < 0.5 的 issue 自动降级一个严重等级

### API 端点

| 方法 | URL | 功能 |
|------|-----|------|
| POST | `/api/reviews/` | 创建审查 |
| GET | `/api/reviews/` | 列表 (支持 project_id 过滤) |
| GET | `/api/reviews/{id}/` | 详情 |
| GET | `/api/reviews/{id}/issues/` | 问题列表 (支持 severity/dimension/file_path 过滤) |
| GET | `/api/reviews/{id}/report/` | 报告 (?output=markdown 或 json) |

## 测试覆盖

| 模块 | 测试数 | 覆盖率 |
|------|--------|--------|
| chunk_manager | 15 | 96% |
| result_aggregator | 13 | 98% |
| report_generator | 13 | 100% |
| review_engine | 4 | 89% |
| tasks | 5 | 94% |
| views | 15 | 95% |
| **总计** | **65** | **98%** |

## 全项目统计

- 总测试: **209** (全部通过)
- 总覆盖率: **96%**

## 代码审查修复

审查发现并修复了以下问题:

- **C1**: 移除 report 视图循环内 ParsedIssue 导入
- **C2**: 进度回调添加异常保护
- **C3**: review.save() 移入 transaction.atomic() 块
- **H3**: Celery 任务使用 transaction.on_commit() 派发
- **H5**: ReportGenerator 解除对 AI 层 ParsedIssue 的依赖，直接接受 ReviewIssue 对象
- **H8**: 移除未使用 import (json, Project)

## 下一阶段

Phase 2: 前端开发 (React)
