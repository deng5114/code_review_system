import re
from dataclasses import dataclass

ENTRY_FILES = frozenset({
    "main.py", "app.py", "index.ts", "index.js", "main.go",
    "main.rs", "Application.java", "manage.py", "server.py",
})

ENTRY_PATTERNS = re.compile(r"(main|app|index|server)\.(py|ts|js|go|rs|java)$", re.IGNORECASE)

CORE_DIRS = frozenset({"src", "app", "lib", "internal", "cmd", "pkg"})

TOKENS_PER_LINE = 4  # 保守估计每行约 4 个 token


@dataclass(frozen=True)
class Chunk:
    files: list[dict]
    estimated_tokens: int
    group_label: str


class ChunkManager:
    def __init__(self, context_window: int = 128000) -> None:
        self._context_window = context_window
        self._max_chunk_tokens = int(context_window * 0.6)

    def plan_chunks(self, files: list[dict]) -> list[Chunk]:
        if not files:
            return []

        total_tokens = self._estimate_total_tokens(files)
        strategy = self.classify_strategy(files, total_tokens)

        if strategy == "full":
            return [Chunk(
                files=list(files),
                estimated_tokens=total_tokens,
                group_label="full",
            )]

        if strategy == "grouped":
            return self._build_grouped_chunks(files)

        return self._build_chunked(files)

    def classify_strategy(self, files: list[dict], total_tokens: int | None = None) -> str:
        if total_tokens is None:
            total_tokens = self._estimate_total_tokens(files)
        half_window = self._context_window * 0.5
        double_window = self._context_window * 2
        if total_tokens <= half_window:
            return "full"
        if total_tokens <= double_window:
            return "grouped"
        return "chunked"

    def group_by_language(self, files: list[dict]) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for f in files:
            lang = f.get("language", "unknown")
            groups.setdefault(lang, []).append(f)
        return groups

    def sort_by_priority(self, files: list[dict]) -> list[dict]:
        def priority(f: dict) -> int:
            path = f["path"]
            basename = path.rsplit("/", 1)[-1] if "/" in path else path
            if basename in ENTRY_FILES or ENTRY_PATTERNS.search(basename):
                return 0
            parts = path.split("/")
            if any(p in CORE_DIRS for p in parts):
                return 1
            return 2
        return sorted(files, key=priority)

    def _estimate_total_tokens(self, files: list[dict]) -> int:
        return sum(f.get("line_count", 0) * TOKENS_PER_LINE for f in files)

    def _build_grouped_chunks(self, files: list[dict]) -> list[Chunk]:
        groups = self.group_by_language(files)
        chunks: list[Chunk] = []
        for lang, group_files in groups.items():
            sorted_files = self.sort_by_priority(group_files)
            tokens = self._estimate_total_tokens(sorted_files)
            if tokens <= self._max_chunk_tokens:
                chunks.append(Chunk(
                    files=sorted_files,
                    estimated_tokens=tokens,
                    group_label=lang,
                ))
            else:
                chunks.extend(self._split_to_size(sorted_files, lang))
        return chunks

    def _build_chunked(self, files: list[dict]) -> list[Chunk]:
        sorted_files = self.sort_by_priority(files)
        return self._split_to_size(sorted_files, "chunk")

    def _split_to_size(self, files: list[dict], label: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        current_files: list[dict] = []
        current_tokens = 0
        idx = 0

        for f in files:
            f_tokens = f.get("line_count", 0) * TOKENS_PER_LINE
            if current_tokens + f_tokens > self._max_chunk_tokens and current_files:
                idx += 1
                chunks.append(Chunk(
                    files=current_files,
                    estimated_tokens=current_tokens,
                    group_label=f"{label}_{idx}",
                ))
                current_files = []
                current_tokens = 0
            current_files.append(f)
            current_tokens += f_tokens

        if current_files:
            idx += 1
            chunks.append(Chunk(
                files=current_files,
                estimated_tokens=current_tokens,
                group_label=f"{label}_{idx}",
            ))
        return chunks
