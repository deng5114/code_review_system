import json
import os
from dataclasses import dataclass, field

# 项目类型配置文件映射
CONFIG_FILE_MAPPING: dict[str, str] = {
    "package.json": "nodejs",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "*.csproj": "csharp",
    "*.sln": "csharp",
    "Gemfile": "ruby",
    "composer.json": "php",
    "mix.exs": "elixir",
    "Package.swift": "swift",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "setup.py": "python",
    "Pipfile": "python",
    "CMakeLists.txt": "cpp",
    "Makefile": "c",
}

# 框架检测规则
FRAMEWORK_PATTERNS: list[dict] = [
    # Python
    {"framework": "django", "markers": ["manage.py"], "file_content": {"requirements.txt": "django", "pyproject.toml": "django"}},
    {"framework": "fastapi", "file_content": {"requirements.txt": "fastapi", "pyproject.toml": "fastapi"}},
    {"framework": "flask", "file_content": {"requirements.txt": "flask", "pyproject.toml": "flask"}},
    # JavaScript / TypeScript
    {"framework": "react", "file_content": {"package.json": "react"}},
    {"framework": "vue", "markers": ["vue.config.js"], "file_content": {"package.json": "vue"}},
    {"framework": "nextjs", "markers": ["next.config.js", "next.config.mjs", "next.config.ts"]},
    {"framework": "express", "file_content": {"package.json": "express"}},
    {"framework": "nestjs", "file_content": {"package.json": "@nestjs/core"}},
    {"framework": "angular", "markers": ["angular.json"]},
    {"framework": "svelte", "markers": ["svelte.config.js"]},
    # Java
    {"framework": "spring-boot", "file_content": {"pom.xml": "springframework", "build.gradle": "springframework", "build.gradle.kts": "springframework"}},
    # Go
    {"framework": "gin", "file_content": {"go.mod": "gin-gonic"}},
    {"framework": "echo", "file_content": {"go.mod": "labstack/echo"}},
    # Rust
    {"framework": "actix", "file_content": {"Cargo.toml": "actix"}},
    {"framework": "axum", "file_content": {"Cargo.toml": "axum"}},
]

# 文件扩展名到语言的补充映射（用于统计，不包含已在 file_filter 中的）
_EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".html": "html", ".css": "css", ".scss": "scss", ".less": "less",
    ".vue": "vue", ".svelte": "svelte",
    ".sql": "sql",
    ".sh": "shell", ".bash": "shell",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
}


@dataclass(frozen=True)
class ProjectDetectionResult:
    project_type: str
    detected_languages: dict[str, int] = field(default_factory=dict)
    detected_frameworks: list[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0


class ProjectDetector:
    """项目类型检测器：识别项目语言、框架、统计代码行数"""

    def detect(self, project_dir: str) -> ProjectDetectionResult:
        if not os.path.isdir(project_dir):
            return ProjectDetectionResult(project_type="unknown")

        files = self._collect_files(project_dir)
        project_type = self._detect_project_type(project_dir, files)
        languages = self._detect_languages(project_dir, files)
        frameworks = self._detect_frameworks(project_dir, files)
        total_lines = self._count_lines(project_dir, files)

        return ProjectDetectionResult(
            project_type=project_type,
            detected_languages=languages,
            detected_frameworks=frameworks,
            total_files=len(files),
            total_lines=total_lines,
        )

    def _collect_files(self, project_dir: str) -> list[str]:
        """收集项目目录中的所有文件（排除 vendor 目录）"""
        from apps.projects.services.file_filter import BINARY_EXTENSIONS, VENDOR_DIRECTORIES

        skip_dirs = VENDOR_DIRECTORIES
        skip_extensions = BINARY_EXTENSIONS

        files: list[str] = []
        for root, dirs, filenames in os.walk(project_dir):
            # 就地修改 dirs 以跳过第三方目录
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in skip_extensions:
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, project_dir)
                files.append(rel_path)
        return files

    def _detect_project_type(self, project_dir: str, files: list[str]) -> str:
        """通过配置文件检测项目类型"""
        filenames = {os.path.basename(f) for f in files}

        # 精确匹配配置文件
        for config_file, project_type in CONFIG_FILE_MAPPING.items():
            if config_file.startswith("*"):
                suffix = config_file[1:]
                if any(fn.endswith(suffix) for fn in filenames):
                    return project_type
            elif config_file in filenames:
                return project_type

        # 按文件扩展名统计推断
        ext_counts: dict[str, int] = {}
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in _EXTENSION_LANGUAGE:
                lang = _EXTENSION_LANGUAGE[ext]
                ext_counts[lang] = ext_counts.get(lang, 0) + 1

        if not ext_counts:
            return "unknown"

        # 选择文件数最多的语言作为项目类型
        primary = max(ext_counts, key=ext_counts.get)  # type: ignore[arg-type]
        type_mapping = {
            "python": "python",
            "javascript": "nodejs",
            "typescript": "nodejs",
            "go": "go",
            "rust": "rust",
            "java": "java",
            "kotlin": "java",
            "csharp": "csharp",
            "cpp": "cpp",
            "c": "c",
        }
        return type_mapping.get(primary, "unknown")

    def _detect_languages(self, project_dir: str, files: list[str]) -> dict[str, int]:
        """统计语言分布（百分比）"""
        lang_lines: dict[str, int] = {}
        total = 0

        for rel_path in files:
            ext = os.path.splitext(rel_path)[1].lower()
            language = _EXTENSION_LANGUAGE.get(ext)
            if not language:
                continue

            full_path = os.path.join(project_dir, rel_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                lines = 0

            lang_lines[language] = lang_lines.get(language, 0) + lines
            total += lines

        if total == 0:
            return {}

        return {lang: round(count / total * 100, 1) for lang, count in sorted(lang_lines.items(), key=lambda x: -x[1])}

    def _detect_frameworks(self, project_dir: str, files: list[str]) -> list[str]:
        """检测项目使用的框架"""
        filenames = {os.path.basename(f) for f in files}
        frameworks: list[str] = []

        for pattern in FRAMEWORK_PATTERNS:
            framework = pattern["framework"]

            # 检查标记文件
            markers = pattern.get("markers", [])
            if any(m in filenames for m in markers):
                frameworks.append(framework)
                continue

            # 检查文件内容中的依赖
            file_content = pattern.get("file_content", {})
            for target_file, keyword in file_content.items():
                full_path = os.path.join(project_dir, target_file)
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if keyword.lower() in content.lower():
                            frameworks.append(framework)
                            break
                    except OSError:
                        pass

        return frameworks

    def _count_lines(self, project_dir: str, files: list[str]) -> int:
        """统计总代码行数"""
        total = 0
        for rel_path in files:
            full_path = os.path.join(project_dir, rel_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    total += sum(1 for _ in f)
            except OSError:
                pass
        return total
