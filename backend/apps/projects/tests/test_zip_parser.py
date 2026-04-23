import os
import tarfile
import zipfile

import pytest

from apps.projects.services.zip_parser import (
    MAX_EXTRACTED_SIZE,
    MAX_FILE_COUNT,
    MAX_UPLOAD_SIZE,
    PathTraversalError,
    ZipBombError,
    ZipParseError,
    ZipParser,
)


class TestZipParserConstants:
    """安全限制常量测试"""

    def test_upload_size_limit(self):
        assert MAX_UPLOAD_SIZE == 100 * 1024 * 1024  # 100MB

    def test_extracted_size_limit(self):
        assert MAX_EXTRACTED_SIZE == 1024 * 1024 * 1024  # 1GB

    def test_file_count_limit(self):
        assert MAX_FILE_COUNT == 10000


class TestZipParse:
    """正常解析测试"""

    def test_parse_zip_file(self, sample_zip_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_zip_file, tmp_dir)
        assert os.path.isdir(result.extract_dir)
        assert len(result.file_list) > 0

    def test_parse_tar_gz_file(self, sample_tar_gz_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_tar_gz_file, tmp_dir)
        assert os.path.isdir(result.extract_dir)
        assert len(result.file_list) > 0

    def test_parse_tar_bz2_file(self, sample_tar_bz2_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_tar_bz2_file, tmp_dir)
        assert os.path.isdir(result.extract_dir)
        assert len(result.file_list) > 0

    def test_parsed_files_are_relative_paths(self, sample_zip_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_zip_file, tmp_dir)
        for path in result.file_list:
            assert not os.path.isabs(path)

    def test_node_modules_excluded(self, sample_zip_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_zip_file, tmp_dir)
        for path in result.file_list:
            parts = path.replace("\\", "/").split("/")
            assert "node_modules" not in parts

    def test_git_directory_excluded(self, sample_zip_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_zip_file, tmp_dir)
        for path in result.file_list:
            parts = path.replace("\\", "/").split("/")
            assert ".git" not in parts

    def test_binary_files_excluded(self, sample_zip_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_zip_file, tmp_dir)
        for path in result.file_list:
            ext = os.path.splitext(path)[1].lower()
            assert ext not in {".png", ".jpg", ".exe", ".zip"}

    def test_detect_file_type_zip(self, sample_zip_file):
        parser = ZipParser()
        assert parser.detect_file_type(sample_zip_file) == "zip"

    def test_detect_file_type_tar_gz(self, sample_tar_gz_file):
        parser = ZipParser()
        assert parser.detect_file_type_tar(sample_tar_gz_file) == "tar.gz"

    def test_detect_file_type_tar_bz2(self, sample_tar_bz2_file):
        parser = ZipParser()
        assert parser.detect_file_type_tar(sample_tar_bz2_file) == "tar.bz2"


class TestZipSecurity:
    """安全测试"""

    def test_reject_path_traversal(self, path_traversal_zip, tmp_dir):
        parser = ZipParser()
        with pytest.raises(PathTraversalError):
            parser.parse(path_traversal_zip, tmp_dir)

    def test_reject_zip_bomb(self, zip_bomb_zip, tmp_dir):
        import unittest.mock

        parser = ZipParser()
        with unittest.mock.patch("apps.projects.services.zip_parser.MAX_EXTRACTED_SIZE", 1024 * 1024):
            with pytest.raises(ZipBombError):
                parser.parse(zip_bomb_zip, tmp_dir)

    def test_reject_unsupported_format(self, tmp_dir):
        """不支持 .rar 等格式"""
        fake_file = os.path.join(tmp_dir, "test.rar")
        with open(fake_file, "wb") as f:
            f.write(b"not a real archive")
        parser = ZipParser()
        with pytest.raises(ZipParseError):
            parser.parse(fake_file, tmp_dir)

    def test_reject_nonexistent_file(self, tmp_dir):
        parser = ZipParser()
        with pytest.raises(ZipParseError):
            parser.parse("/nonexistent/file.zip", tmp_dir)

    def test_reject_oversized_upload(self, tmp_dir):
        """超过 100MB 的文件应被拒绝"""
        big_file = os.path.join(tmp_dir, "big.zip")
        # 创建一个假装超过大小限制的文件（通过 monkeypatch 降低阈值测试）
        import unittest.mock

        parser = ZipParser()
        with unittest.mock.patch("apps.projects.services.zip_parser.MAX_UPLOAD_SIZE", 100):
            with open(big_file, "wb") as f:
                f.write(b"x" * 200)
            with pytest.raises(ZipParseError, match="文件大小"):
                parser.parse(big_file, tmp_dir)

    def test_file_count_limit(self, tmp_dir):
        """文件数量超过限制时应被拒绝"""
        zip_path = os.path.join(tmp_dir, "many_files.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            for i in range(50):
                zf.writestr(f"file_{i}.txt", f"content {i}\n")

        import unittest.mock

        parser = ZipParser()
        with unittest.mock.patch("apps.projects.services.zip_parser.MAX_FILE_COUNT", 10):
            with pytest.raises(ZipParseError):
                parser.parse(zip_path, tmp_dir)


class TestTarSecurity:
    """tar 格式安全测试"""

    def test_tar_path_traversal(self, tmp_dir):
        """tar 文件中的路径穿越应被拒绝"""
        tar_path = os.path.join(tmp_dir, "malicious.tar.gz")
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="../../../etc/passwd")
            data = b"root:x:0:0::/root:/bin/bash\n"
            info.size = len(data)
            tf.addfile(info, fileobj=__import__("io").BytesIO(data))

        parser = ZipParser()
        with pytest.raises(PathTraversalError):
            parser.parse(tar_path, tmp_dir)

    def test_tar_bomb_detection(self, tmp_dir):
        """tar 解压炸弹应被检测"""
        tar_path = os.path.join(tmp_dir, "bomb.tar.gz")
        with tarfile.open(tar_path, "w:gz") as tf:
            large_data = b"A" * (5 * 1024 * 1024)  # 5MB
            for i in range(5):
                info = tarfile.TarInfo(name=f"huge_{i}.txt")
                info.size = len(large_data)
                tf.addfile(info, fileobj=__import__("io").BytesIO(large_data))

        import unittest.mock

        parser = ZipParser()
        with unittest.mock.patch("apps.projects.services.zip_parser.MAX_EXTRACTED_SIZE", 1024 * 1024):
            with pytest.raises(ZipBombError):
                parser.parse(tar_path, tmp_dir)


class TestParseResult:
    """ParseResult dataclass 测试"""

    def test_parse_result_attributes(self, sample_zip_file, tmp_dir):
        parser = ZipParser()
        result = parser.parse(sample_zip_file, tmp_dir)
        assert hasattr(result, "extract_dir")
        assert hasattr(result, "file_list")
        assert hasattr(result, "total_size")
        assert result.total_size >= 0
