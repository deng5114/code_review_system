import os

import pytest

from apps.projects.services.file_filter import (
    BINARY_EXTENSIONS,
    FilteredFile,
    FileFilter,
    LANGUAGE_MAP,
    VENDOR_DIRECTORIES,
)


class TestFilteredFile:
    """FilteredFile dataclass 测试"""

    def test_create_filtered_file(self):
        f = FilteredFile(
            path="src/index.ts",
            language="typescript",
            is_binary=False,
            is_vendor=False,
            is_generated=False,
            line_count=10,
            file_size=256,
        )
        assert f.path == "src/index.ts"
        assert f.language == "typescript"
        assert f.is_binary is False
        assert f.line_count == 10

    def test_filtered_file_defaults(self):
        f = FilteredFile(path="main.py", language="python")
        assert f.is_binary is False
        assert f.is_vendor is False
        assert f.is_generated is False
        assert f.line_count == 0
        assert f.file_size == 0


class TestConstants:
    """常量配置测试"""

    def test_binary_extensions_contains_common_types(self):
        assert ".png" in BINARY_EXTENSIONS
        assert ".jpg" in BINARY_EXTENSIONS
        assert ".exe" in BINARY_EXTENSIONS
        assert ".pdf" in BINARY_EXTENSIONS
        assert ".zip" in BINARY_EXTENSIONS

    def test_vendor_directories_contains_common_dirs(self):
        assert "node_modules" in VENDOR_DIRECTORIES
        assert "venv" in VENDOR_DIRECTORIES
        assert ".git" in VENDOR_DIRECTORIES
        assert "__pycache__" in VENDOR_DIRECTORIES

    def test_language_map_covers_major_languages(self):
        assert ".py" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".py"] == "python"
        assert ".ts" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".ts"] == "typescript"
        assert ".go" in LANGUAGE_MAP
        assert ".rs" in LANGUAGE_MAP
        assert ".java" in LANGUAGE_MAP


class TestFileFilter:
    """FileFilter 类测试"""

    def test_filter_binary_files(self, sample_project_dir):
        ff = FileFilter()
        files = [
            "src/index.ts",
            "assets/logo.png",
            "dist/app.exe",
            "README.md",
        ]
        result = ff.filter_files(files, sample_project_dir)
        paths = [f.path for f in result]
        assert "assets/logo.png" not in paths
        assert "dist/app.exe" not in paths
        assert "src/index.ts" in paths
        assert "README.md" in paths

    def test_filter_vendor_directories(self, sample_project_dir):
        ff = FileFilter()
        files = [
            "src/index.ts",
            "node_modules/express/index.js",
            ".git/HEAD",
            "package.json",
        ]
        result = ff.filter_files(files, sample_project_dir)
        paths = [f.path for f in result]
        assert "node_modules/express/index.js" not in paths
        assert ".git/HEAD" not in paths
        assert "src/index.ts" in paths
        assert "package.json" in paths

    def test_detect_file_language(self, sample_project_dir):
        ff = FileFilter()
        files = [
            "src/index.ts",
            "src/utils/helpers.ts",
            "package.json",
            "README.md",
        ]
        result = ff.filter_files(files, sample_project_dir)
        ts_files = [f for f in result if f.language == "typescript"]
        json_files = [f for f in result if f.language == "json"]
        md_files = [f for f in result if f.language == "markdown"]
        assert len(ts_files) == 2
        assert len(json_files) == 1
        assert len(md_files) == 1

    def test_unknown_extension_gets_empty_language(self, sample_project_dir):
        ff = FileFilter()
        files = ["Makefile", "Dockerfile"]
        result = ff.filter_files(files, sample_project_dir)
        for f in result:
            if f.path in ("Makefile", "Dockerfile"):
                assert f.language == ""

    def test_filter_empty_file_list(self, sample_project_dir):
        ff = FileFilter()
        result = ff.filter_files([], sample_project_dir)
        assert result == []

    def test_count_lines(self, sample_project_dir):
        ff = FileFilter()
        files = ["src/index.ts"]
        result = ff.filter_files(files, sample_project_dir)
        assert len(result) == 1
        assert result[0].line_count == 2

    def test_file_size_tracking(self, sample_project_dir):
        ff = FileFilter()
        files = ["src/index.ts"]
        result = ff.filter_files(files, sample_project_dir)
        assert len(result) == 1
        assert result[0].file_size > 0

    def test_generated_file_detection(self, tmp_dir):
        ff = FileFilter()
        with open(os.path.join(tmp_dir, "package-lock.json"), "w") as f:
            f.write("{}")

        src_dir = os.path.join(tmp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "main.ts"), "w") as f:
            f.write("test line 1\ntest line 2\n")

        result = ff.filter_files(
            ["package-lock.json", "src/main.ts"],
            tmp_dir,
        )
        lock = next(f for f in result if f.path == "package-lock.json")
        assert lock.is_generated is True

    def test_vendor_directory_variants(self):
        """测试各种第三方目录模式"""
        ff = FileFilter()
        assert ff._is_vendor_path("node_modules/express/index.js")
        assert ff._is_vendor_path("venv/lib/python3.12/site.py")
        assert ff._is_vendor_path("lib/python3.12/site-packages/requests/__init__.py")
        assert ff._is_vendor_path(".git/config")
        assert ff._is_vendor_path("__pycache__/module.cpython-312.pyc")
        assert not ff._is_vendor_path("src/myapp/models.py")
        assert not ff._is_vendor_path("tests/test_main.py")
