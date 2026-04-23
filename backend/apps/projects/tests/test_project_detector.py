import os

import pytest

from apps.projects.services.project_detector import (
    ProjectDetectionResult,
    ProjectDetector,
)


class TestProjectDetectionResult:
    """ProjectDetectionResult dataclass 测试"""

    def test_create_result(self):
        result = ProjectDetectionResult(
            project_type="python",
            detected_languages={"python": 80, "html": 20},
            detected_frameworks=["django"],
            total_files=10,
            total_lines=500,
        )
        assert result.project_type == "python"
        assert "python" in result.detected_languages
        assert "django" in result.detected_frameworks

    def test_result_defaults(self):
        result = ProjectDetectionResult(
            project_type="unknown",
            detected_languages={},
            detected_frameworks=[],
            total_files=0,
            total_lines=0,
        )
        assert result.detected_languages == {}
        assert result.detected_frameworks == []


class TestDetectNodejsProject:
    """Node.js / TypeScript 项目检测"""

    def test_detect_nodejs_from_package_json(self, sample_project_dir):
        detector = ProjectDetector()
        result = detector.detect(sample_project_dir)
        assert result.project_type == "nodejs"
        assert "typescript" in result.detected_languages

    def test_detect_react_framework(self, sample_project_dir):
        detector = ProjectDetector()
        result = detector.detect(sample_project_dir)
        assert "express" in result.detected_frameworks

    def test_detect_language_distribution(self, sample_project_dir):
        detector = ProjectDetector()
        result = detector.detect(sample_project_dir)
        assert result.total_files > 0
        assert result.total_lines > 0


class TestDetectPythonProject:
    """Python 项目检测"""

    def test_detect_python_from_requirements(self, sample_python_dir):
        detector = ProjectDetector()
        result = detector.detect(sample_python_dir)
        assert result.project_type == "python"

    def test_detect_django_framework(self, sample_python_dir):
        detector = ProjectDetector()
        result = detector.detect(sample_python_dir)
        assert "django" in result.detected_frameworks

    def test_python_language_distribution(self, sample_python_dir):
        detector = ProjectDetector()
        result = detector.detect(sample_python_dir)
        assert "python" in result.detected_languages
        assert result.detected_languages["python"] > 0


class TestDetectGoProject:
    """Go 项目检测"""

    def test_detect_go_project(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "go-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "go.mod"), "w") as f:
            f.write("module github.com/test/myapp\ngo 1.22\n")
        with open(os.path.join(project_dir, "main.go"), "w") as f:
            f.write("package main\n\nfunc main() {\n\tprintln(\"hello\")\n}\n")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert result.project_type == "go"
        assert "go" in result.detected_languages


class TestDetectRustProject:
    """Rust 项目检测"""

    def test_detect_rust_project(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "rust-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "Cargo.toml"), "w") as f:
            f.write("[package]\nname = \"myapp\"\nversion = \"0.1.0\"\n")
        src_dir = os.path.join(project_dir, "src")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "main.rs"), "w") as f:
            f.write("fn main() {\n    println!(\"hello\");\n}\n")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert result.project_type == "rust"
        assert "rust" in result.detected_languages


class TestDetectJavaProject:
    """Java 项目检测"""

    def test_detect_java_from_pom(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "java-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "pom.xml"), "w") as f:
            f.write("<project><modelVersion>4.0.0</modelVersion></project>")
        src_dir = os.path.join(project_dir, "src", "main", "java")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "App.java"), "w") as f:
            f.write("public class App {\n    public static void main(String[] args) {}\n}\n")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert result.project_type == "java"

    def test_detect_spring_boot(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "spring-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "pom.xml"), "w") as f:
            f.write(
                "<project>"
                "<dependencies>"
                "<dependency>"
                "<groupId>org.springframework.boot</groupId>"
                "</dependency>"
                "</dependencies>"
                "</project>"
            )
        src_dir = os.path.join(project_dir, "src", "main", "java")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "App.java"), "w") as f:
            f.write("@SpringBootApplication\npublic class App {}\n")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert "spring-boot" in result.detected_frameworks


class TestDetectCSharpProject:
    """C# 项目检测"""

    def test_detect_csharp_project(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "csharp-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "Program.cs"), "w") as f:
            f.write("using System;\nclass Program {\n    static void Main() {}\n}\n")
        with open(os.path.join(project_dir, "myapp.csproj"), "w") as f:
            f.write("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert result.project_type == "csharp"


class TestDetectCppProject:
    """C/C++ 项目检测"""

    def test_detect_cpp_project(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "cpp-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "main.cpp"), "w") as f:
            f.write("#include <iostream>\nint main() {\n    std::cout << \"hello\";\n    return 0;\n}\n")
        with open(os.path.join(project_dir, "CMakeLists.txt"), "w") as f:
            f.write("cmake_minimum_required(VERSION 3.20)\nproject(myapp)\n")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert result.project_type in ("cpp", "c")


class TestEdgeCases:
    """边缘情况测试"""

    def test_empty_directory(self, tmp_dir):
        empty_dir = os.path.join(tmp_dir, "empty-project")
        os.makedirs(empty_dir)
        detector = ProjectDetector()
        result = detector.detect(empty_dir)
        assert result.project_type == "unknown"
        assert result.total_files == 0

    def test_single_readme_project(self, tmp_dir):
        project_dir = os.path.join(tmp_dir, "readme-only")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "README.md"), "w") as f:
            f.write("# My Project\n")

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        assert result.project_type == "unknown"

    def test_language_distribution_percentages(self, tmp_dir):
        """验证语言分布百分比总和合理"""
        project_dir = os.path.join(tmp_dir, "mixed-project")
        os.makedirs(project_dir)
        with open(os.path.join(project_dir, "main.py"), "w") as f:
            f.write("print('hello')\n" * 50)
        with open(os.path.join(project_dir, "app.js"), "w") as f:
            f.write("console.log('hello');\n" * 30)
        with open(os.path.join(project_dir, "style.css"), "w") as f:
            f.write("body { margin: 0; }\n" * 20)

        detector = ProjectDetector()
        result = detector.detect(project_dir)
        total_pct = sum(result.detected_languages.values())
        assert total_pct <= 100
