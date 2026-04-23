import io
import os
import tarfile
import zipfile
from dataclasses import dataclass

from apps.projects.services.file_filter import BINARY_EXTENSIONS, VENDOR_DIRECTORIES

MAX_UPLOAD_SIZE = 100 * 1024 * 1024       # 100MB
MAX_EXTRACTED_SIZE = 1024 * 1024 * 1024    # 1GB
MAX_FILE_COUNT = 10000

SKIP_DIRS = VENDOR_DIRECTORIES


class ZipParseError(Exception):
    """压缩包解析通用错误"""


class ZipBombError(ZipParseError):
    """解压炸弹检测"""


class PathTraversalError(ZipParseError):
    """路径穿越攻击检测"""


@dataclass(frozen=True)
class ParseResult:
    extract_dir: str
    file_list: list[str]
    total_size: int


class ZipParser:
    """压缩包解析器：支持 .zip / .tar.gz / .tar.bz2，内置安全检查"""

    def parse(self, file_path: str, output_dir: str) -> ParseResult:
        self._validate_file(file_path)
        file_type = self._detect_format(file_path)

        extract_dir = os.path.join(output_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        if file_type == "zip":
            self._extract_zip(file_path, extract_dir)
        elif file_type in ("tar.gz", "tar.bz2", "tar"):
            self._extract_tar(file_path, extract_dir, file_type)
        else:
            raise ZipParseError(f"不支持的文件格式: {file_type}")

        # 查找实际项目根目录（如果解压后只有一级目录）
        project_root = self._find_project_root(extract_dir)
        file_list = self._collect_safe_files(project_root)
        total_size = self._calculate_total_size(project_root, file_list)

        return ParseResult(
            extract_dir=project_root,
            file_list=file_list,
            total_size=total_size,
        )

    def detect_file_type(self, file_path: str) -> str:
        """检测文件类型（基于 magic bytes 或扩展名）"""
        ext = self._get_extension(file_path)
        if ext == ".zip":
            return "zip"
        return "unknown"

    def detect_file_type_tar(self, file_path: str) -> str:
        """检测 tar 文件类型"""
        ext = self._get_extension(file_path)
        if ext == ".tar.gz" or ext == ".tgz":
            return "tar.gz"
        if ext == ".tar.bz2" or ext == ".tbz2":
            return "tar.bz2"
        if ext == ".tar":
            return "tar"
        return "unknown"

    def _validate_file(self, file_path: str) -> None:
        if not os.path.isfile(file_path):
            raise ZipParseError(f"文件不存在: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > MAX_UPLOAD_SIZE:
            raise ZipParseError(f"文件大小超过限制: {file_size} bytes (最大 {MAX_UPLOAD_SIZE} bytes)")

        ext = self._get_extension(file_path)
        supported = {".zip", ".tar.gz", ".tar.bz2", ".tgz", ".tbz2", ".tar"}
        if ext not in supported:
            raise ZipParseError(f"不支持的文件格式: {ext}")

    def _detect_format(self, file_path: str) -> str:
        ext = self._get_extension(file_path)
        if ext == ".zip":
            return "zip"
        if ext in (".tar.gz", ".tgz"):
            return "tar.gz"
        if ext in (".tar.bz2", ".tbz2"):
            return "tar.bz2"
        if ext == ".tar":
            return "tar"
        return "unknown"

    def _extract_zip(self, file_path: str, extract_dir: str) -> None:
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # 安全预检查
                total_size = 0
                file_count = 0
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    # 路径穿越检查
                    if self._has_path_traversal(info.filename):
                        raise PathTraversalError(f"检测到路径穿越攻击: {info.filename}")
                    total_size += info.file_size
                    file_count += 1
                    if file_count > MAX_FILE_COUNT:
                        raise ZipParseError(f"文件数量超过限制: 最大 {MAX_FILE_COUNT}")
                    if total_size > MAX_EXTRACTED_SIZE:
                        raise ZipBombError(
                            f"解压后大小超过限制: {total_size} bytes (最大 {MAX_EXTRACTED_SIZE} bytes)"
                        )

                zf.extractall(extract_dir)
        except zipfile.BadZipFile as e:
            raise ZipParseError(f"无效的 ZIP 文件: {e}") from e

    def _extract_tar(self, file_path: str, extract_dir: str, file_type: str) -> None:
        mode = "r:gz" if file_type == "tar.gz" else "r:bz2" if file_type == "tar.bz2" else "r:"
        try:
            with tarfile.open(file_path, mode) as tf:
                total_size = 0
                file_count = 0
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    # 路径穿越检查
                    if self._has_path_traversal(member.name):
                        raise PathTraversalError(f"检测到路径穿越攻击: {member.name}")
                    total_size += member.size
                    file_count += 1
                    if file_count > MAX_FILE_COUNT:
                        raise ZipParseError(f"文件数量超过限制: 最大 {MAX_FILE_COUNT}")
                    if total_size > MAX_EXTRACTED_SIZE:
                        raise ZipBombError(
                            f"解压后大小超过限制: {total_size} bytes (最大 {MAX_EXTRACTED_SIZE} bytes)"
                        )

                tf.extractall(extract_dir, filter="data")
        except tarfile.TarError as e:
            raise ZipParseError(f"无效的 TAR 文件: {e}") from e

    def _has_path_traversal(self, path: str) -> bool:
        normalized = os.path.normpath(path).replace("\\", "/")
        return ".." in normalized.split("/")

    def _find_project_root(self, extract_dir: str) -> str:
        """如果解压后只有一个顶层目录，则进入该目录"""
        entries = os.listdir(extract_dir)
        if len(entries) == 1:
            single = os.path.join(extract_dir, entries[0])
            if os.path.isdir(single):
                return single
        return extract_dir

    def _collect_safe_files(self, project_root: str) -> list[str]:
        """收集安全文件（排除 vendor 目录和二进制文件）"""
        files: list[str] = []
        for root, dirs, filenames in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in BINARY_EXTENSIONS:
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, project_root)
                # 再次检查路径穿越
                if self._has_path_traversal(rel_path):
                    continue
                files.append(rel_path)
        return files

    def _calculate_total_size(self, project_root: str, file_list: list[str]) -> int:
        total = 0
        for rel_path in file_list:
            full_path = os.path.join(project_root, rel_path)
            try:
                total += os.path.getsize(full_path)
            except OSError:
                pass
        return total

    @staticmethod
    def _get_extension(path: str) -> str:
        lower = path.lower()
        # 检查复合扩展名
        for ext in (".tar.gz", ".tar.bz2"):
            if lower.endswith(ext):
                return ext
        _, ext = os.path.splitext(lower)
        return ext
