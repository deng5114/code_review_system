# Phase 1 Step 2: 项目上传与解析服务 — 实施计划

## 目标

实现压缩包上传、解压、项目类型检测、文件过滤功能，支持 .zip/.tar.gz/.tar.bz2 格式。

## 实施步骤（TDD 驱动）

### 阶段 A: 测试基础设施

1. **pytest.ini** — 配置 pytest + Django
2. **tests/conftest.py** — 测试 fixtures（临时目录、样本 zip 文件等）

### 阶段 B: file_filter 服务（最简单，优先）

3. **tests/test_file_filter.py** — 先写测试 (RED)
   - 过滤二进制文件、第三方目录、生成代码
   - 检测文件语言、处理空列表
4. **services/file_filter.py** — 实现功能 (GREEN)
   - FilteredFile dataclass、FileFilter 类
   - BINARY_EXTENSIONS、VENDOR_DIRECTORIES、LANGUAGE_MAP 常量
5. **重构** — 优化代码结构 (IMPROVE)

### 阶段 C: project_detector 服务

6. **tests/test_project_detector.py** — 先写测试 (RED)
   - 检测 Node.js/Python/Go/Rust/Java/C#/C++ 项目
   - 检测 Django/React/Spring Boot 框架
   - 统计语言分布和代码行数
7. **services/project_detector.py** — 实现功能 (GREEN)
   - ProjectDetectionResult dataclass、ProjectDetector 类
   - CONFIG_FILE_MAPPING、FRAMEWORK_PATTERNS 常量
8. **重构** — 优化代码结构 (IMPROVE)

### 阶段 D: zip_parser 服务（最复杂）

9. **tests/test_zip_parser.py** — 先写测试 (RED)
   - 支持 .zip/.tar.gz/.tar.bz2
   - 安全测试: 解压炸弹、路径穿越、文件数量限制
   - 排除 node_modules/.git/venv 等
10. **services/zip_parser.py** — 实现功能 (GREEN)
    - ZipParser 类 + 自定义异常 (ZipParseError, ZipBombError, PathTraversalError)
    - 安全限制: 100MB 上传、1GB 解压、10000 文件
11. **重构** — 优化代码结构 (IMPROVE)

### 阶段 E: API 层

12. **serializers.py** — ProjectUploadSerializer、ProjectSerializer、FileTreeNodeSerializer
13. **views.py** — ProjectViewSet (upload、list、detail、files、file_content)
14. **urls.py** — 更新路由配置

### 阶段 F: 集成测试与验证

15. **tests/test_views.py** — API 集成测试
16. **覆盖率验证** — pytest --cov >= 80%

## 新建文件（15 个）

```
backend/
├── pytest.ini
├── apps/projects/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_filter.py
│   │   ├── project_detector.py
│   │   └── zip_parser.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_file_filter.py
│   │   ├── test_project_detector.py
│   │   ├── test_zip_parser.py
│   │   └── test_views.py
│   └── serializers.py
```

## 安全要求

| 检查项 | 限制值 |
|--------|--------|
| 上传文件大小 | ≤ 100MB |
| 解压后总大小 | ≤ 1GB |
| 文件数量 | ≤ 10000 |
| 路径穿越 | 拒绝包含 `..` 的路径 |
| 文件类型 | 仅 .zip/.tar.gz/.tar.bz2 |

## 验收标准

- 上传 TypeScript 项目 zip → 正确识别为 Node.js，语言分布准确
- 上传 Python 项目 zip → 识别 Python + Django 框架
- 测试覆盖率 ≥ 80%
- 拒绝超大文件、解压炸弹、路径穿越攻击
