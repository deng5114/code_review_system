import os
from dataclasses import dataclass, field

BINARY_EXTENSIONS = frozenset({
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp", ".tiff", ".tif",
    # Audio/Video
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac", ".ogg", ".wmv",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    # Executables
    ".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o", ".a",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Other binary
    ".pyc", ".pyo", ".class", ".jar", ".war",
    ".sqlite", ".db", ".dat",
    ".wasm",
})

VENDOR_DIRECTORIES = frozenset({
    "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", ".git", ".svn", ".hg",
    "vendor", "third_party", "thirdparty",
    "dist", "build", "out", "target",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "site-packages",
    ".next", ".nuxt", ".cache",
    "Pods", "Carthage", ".spm",
    ".gradle", ".idea", ".vscode",
    "coverage", ".coverage", "htmlcov",
})

GENERATED_FILE_PATTERNS = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "composer.lock", "Gemfile.lock", "poetry.lock",
    "Cargo.lock", "go.sum", "mix.lock",
    "Pipfile.lock",
})

GENERATED_FILE_SUFFIXES = frozenset({
    ".min.js", ".min.css",
    ".js.map", ".css.map",
    ".d.ts",  # TypeScript declaration files (generated)
})

LANGUAGE_MAP: dict[str, str] = {
    # Python
    ".py": "python", ".pyi": "python", ".pyx": "python",
    # JavaScript / TypeScript
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".mjs": "javascript", ".cjs": "javascript",
    # Web
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".vue": "vue", ".svelte": "svelte",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # Java / JVM
    ".java": "java", ".kt": "kotlin", ".scala": "scala", ".groovy": "groovy",
    # C / C++
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".hpp": "cpp", ".hxx": "cpp",
    # C#
    ".cs": "csharp",
    # Ruby
    ".rb": "ruby", ".erb": "ruby",
    # PHP
    ".php": "php",
    # Swift / Obj-C
    ".swift": "swift", ".m": "objective-c", ".mm": "objective-c++",
    # Shell
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    # Config / Data
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".xml": "xml", ".ini": "ini", ".cfg": "ini",
    ".env": "dotenv",
    # Markup
    ".md": "markdown", ".rst": "restructuredtext", ".txt": "text",
    ".adoc": "asciidoc",
    # Database
    ".sql": "sql",
    # Other
    ".dockerfile": "dockerfile",
    ".graphql": "graphql", ".gql": "graphql",
    ".proto": "protobuf",
    ".tf": "terraform", ".hcl": "hcl",
    ".lua": "lua",
    ".r": "r", ".R": "r",
    ".dart": "dart",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".nim": "nim",
    ".zig": "zig",
}


@dataclass(frozen=True)
class FilteredFile:
    path: str
    language: str
    is_binary: bool = False
    is_vendor: bool = False
    is_generated: bool = False
    line_count: int = 0
    file_size: int = 0


class FileFilter:
    """文件过滤器：排除二进制文件、第三方目录、生成代码"""

    def filter_files(
        self, file_paths: list[str], base_dir: str
    ) -> list[FilteredFile]:
        if not file_paths:
            return []

        results: list[FilteredFile] = []
        for path in file_paths:
            filtered = self._process_file(path, base_dir)
            if filtered is not None:
                results.append(filtered)
        return results

    def _process_file(self, rel_path: str, base_dir: str) -> FilteredFile | None:
        ext = self._get_extension(rel_path)
        filename = os.path.basename(rel_path)

        is_vendor = self._is_vendor_path(rel_path)
        if is_vendor:
            return None

        is_binary = ext in BINARY_EXTENSIONS
        if is_binary:
            return None

        language = LANGUAGE_MAP.get(ext, "")
        is_generated = self._is_generated(filename, ext)

        line_count = 0
        file_size = 0
        full_path = os.path.join(base_dir, rel_path)
        if os.path.isfile(full_path):
            file_size = os.path.getsize(full_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
            except (OSError, UnicodeDecodeError):
                pass

        return FilteredFile(
            path=rel_path,
            language=language,
            is_binary=is_binary,
            is_vendor=is_vendor,
            is_generated=is_generated,
            line_count=line_count,
            file_size=file_size,
        )

    def _is_vendor_path(self, rel_path: str) -> bool:
        parts = rel_path.replace("\\", "/").split("/")
        return any(part in VENDOR_DIRECTORIES for part in parts)

    def _is_generated(self, filename: str, ext: str) -> bool:
        if filename in GENERATED_FILE_PATTERNS:
            return True
        return any(filename.endswith(s) for s in GENERATED_FILE_SUFFIXES)

    @staticmethod
    def _get_extension(path: str) -> str:
        _, ext = os.path.splitext(path)
        return ext.lower()
