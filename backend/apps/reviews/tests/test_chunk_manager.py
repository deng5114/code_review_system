import pytest

from apps.reviews.services.chunk_manager import Chunk, ChunkManager


@pytest.fixture
def manager():
    return ChunkManager(context_window=8000)


def _make_file(path: str, language: str, line_count: int, content: str = "") -> dict:
    return {
        "path": path,
        "language": language,
        "line_count": line_count,
        "content": content or f"# {path}\n" + "x = 1\n" * (line_count - 1),
    }


class TestChunk:
    def test_chunk_fields(self):
        chunk = Chunk(
            files=[_make_file("a.py", "python", 5)],
            estimated_tokens=100,
            group_label="python",
        )
        assert len(chunk.files) == 1
        assert chunk.estimated_tokens == 100
        assert chunk.group_label == "python"

    def test_chunk_is_frozen(self):
        chunk = Chunk(files=[], estimated_tokens=0, group_label="")
        with pytest.raises(AttributeError):
            chunk.estimated_tokens = 999


class TestClassifyStrategy:
    def test_small_project_uses_full(self, manager):
        files = [_make_file("main.py", "python", 10)]
        strategy = manager.classify_strategy(files, total_tokens=500)
        assert strategy == "full"

    def test_medium_project_uses_grouped(self, manager):
        files = [
            _make_file("a.py", "python", 50),
            _make_file("b.py", "python", 50),
            _make_file("c.ts", "typescript", 50),
        ]
        strategy = manager.classify_strategy(files, total_tokens=10000)
        assert strategy == "grouped"

    def test_large_project_uses_chunked(self, manager):
        files = [_make_file(f"file{i}.py", "python", 100) for i in range(50)]
        strategy = manager.classify_strategy(files, total_tokens=50000)
        assert strategy == "chunked"


class TestPlanChunks:
    def test_full_strategy_single_chunk(self, manager):
        files = [_make_file("main.py", "python", 10)]
        chunks = manager.plan_chunks(files)
        assert len(chunks) == 1
        assert chunks[0].group_label == "full"

    def test_grouped_strategy_by_language(self, manager):
        files = [
            _make_file("a.py", "python", 600),
            _make_file("b.py", "python", 600),
            _make_file("c.ts", "typescript", 600),
            _make_file("d.ts", "typescript", 600),
        ]
        chunks = manager.plan_chunks(files)
        labels = {c.group_label for c in chunks}
        assert "python" in labels
        assert "typescript" in labels

    def test_chunked_strategy_multiple_chunks(self):
        mgr = ChunkManager(context_window=500)
        files = [_make_file(f"f{i}.py", "python", 50) for i in range(20)]
        chunks = mgr.plan_chunks(files)
        assert len(chunks) > 1

    def test_empty_files_returns_empty(self, manager):
        chunks = manager.plan_chunks([])
        assert chunks == []

    def test_chunk_contains_all_files(self, manager):
        files = [
            _make_file("a.py", "python", 5),
            _make_file("b.py", "python", 5),
            _make_file("c.py", "python", 5),
        ]
        chunks = manager.plan_chunks(files)
        all_paths = {f["path"] for c in chunks for f in c.files}
        assert all_paths == {"a.py", "b.py", "c.py"}

    def test_each_file_appears_once(self, manager):
        files = [_make_file(f"f{i}.py", "python", 5) for i in range(10)]
        chunks = manager.plan_chunks(files)
        all_paths = [f["path"] for c in chunks for f in c.files]
        assert len(all_paths) == len(set(all_paths))


class TestGroupByLanguage:
    def test_groups_correctly(self, manager):
        files = [
            _make_file("a.py", "python", 10),
            _make_file("b.ts", "typescript", 10),
            _make_file("c.py", "python", 10),
        ]
        groups = manager.group_by_language(files)
        assert len(groups["python"]) == 2
        assert len(groups["typescript"]) == 1

    def test_empty_input(self, manager):
        groups = manager.group_by_language([])
        assert groups == {}


class TestSortByPriority:
    def test_entry_files_first(self, manager):
        files = [
            _make_file("utils.py", "python", 10),
            _make_file("main.py", "python", 10),
            _make_file("config.py", "python", 10),
        ]
        sorted_files = manager.sort_by_priority(files)
        assert sorted_files[0]["path"] == "main.py"

    def test_core_logic_before_config(self, manager):
        files = [
            _make_file("settings.json", "json", 10),
            _make_file("src/app.py", "python", 10),
        ]
        sorted_files = manager.sort_by_priority(files)
        assert sorted_files[0]["path"] == "src/app.py"
