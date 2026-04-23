import os
import tarfile
import tempfile
import zipfile

import pytest


@pytest.fixture
def tmp_dir():
    """提供一个临时目录，测试结束后自动清理"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_project_dir(tmp_dir):
    """创建一个模拟的 Node.js 项目目录结构"""
    project_root = os.path.join(tmp_dir, "sample-nodejs-project")
    os.makedirs(project_root)

    # package.json
    with open(os.path.join(project_root, "package.json"), "w") as f:
        f.write('{"name": "test-app", "dependencies": {"express": "^4.18.0"}}')

    # src/index.ts
    src_dir = os.path.join(project_root, "src")
    os.makedirs(src_dir)
    with open(os.path.join(src_dir, "index.ts"), "w") as f:
        f.write("const app = express();\napp.listen(3000);\n")

    # src/utils/helpers.ts
    utils_dir = os.path.join(src_dir, "utils")
    os.makedirs(utils_dir)
    with open(os.path.join(utils_dir, "helpers.ts"), "w") as f:
        f.write("export function add(a: number, b: number): number {\n  return a + b;\n}\n")

    # node_modules (should be filtered)
    nm_dir = os.path.join(project_root, "node_modules", "express")
    os.makedirs(nm_dir)
    with open(os.path.join(nm_dir, "index.js"), "w") as f:
        f.write("module.exports = {};\n")

    # .git (should be filtered)
    git_dir = os.path.join(project_root, ".git", "objects")
    os.makedirs(git_dir)
    with open(os.path.join(git_dir, "HEAD"), "w") as f:
        f.write("ref: refs/heads/main\n")

    # Binary file (should be filtered)
    with open(os.path.join(project_root, "image.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    return project_root


@pytest.fixture
def sample_python_dir(tmp_dir):
    """创建一个模拟的 Python/Django 项目目录结构"""
    project_root = os.path.join(tmp_dir, "sample-python-project")
    os.makedirs(project_root)

    # manage.py
    with open(os.path.join(project_root, "manage.py"), "w") as f:
        f.write("#!/usr/bin/env python\nimport django\n")

    # requirements.txt
    with open(os.path.join(project_root, "requirements.txt"), "w") as f:
        f.write("Django>=5.0\ndjangorestframework>=3.15\n")

    # myproject/settings.py
    pkg_dir = os.path.join(project_root, "myproject")
    os.makedirs(pkg_dir)
    with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(pkg_dir, "settings.py"), "w") as f:
        f.write("INSTALLED_APPS = ['django.contrib.admin']\n")

    # myapp/models.py
    app_dir = os.path.join(project_root, "myapp")
    os.makedirs(app_dir)
    with open(os.path.join(app_dir, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(app_dir, "models.py"), "w") as f:
        f.write("from django.db import models\n\nclass Item(models.Model):\n    name = models.CharField(max_length=100)\n")

    # venv (should be filtered)
    venv_dir = os.path.join(project_root, "venv", "lib", "python3.12")
    os.makedirs(venv_dir)
    with open(os.path.join(venv_dir, "site.py"), "w") as f:
        f.write("# virtualenv file\n")

    return project_root


def _create_zip(project_dir, zip_path):
    """将目录打包成 .zip 文件"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(project_dir))
                zf.write(file_path, arcname)


def _create_tar_gz(project_dir, tar_path):
    """将目录打包成 .tar.gz 文件"""
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(project_dir, arcname=os.path.basename(project_dir))


def _create_tar_bz2(project_dir, tar_path):
    """将目录打包成 .tar.bz2 文件"""
    with tarfile.open(tar_path, "w:bz2") as tf:
        tf.add(project_dir, arcname=os.path.basename(project_dir))


@pytest.fixture
def sample_zip_file(sample_project_dir, tmp_dir):
    """创建一个 .zip 测试文件"""
    zip_path = os.path.join(tmp_dir, "test-project.zip")
    _create_zip(sample_project_dir, zip_path)
    return zip_path


@pytest.fixture
def sample_tar_gz_file(sample_project_dir, tmp_dir):
    """创建一个 .tar.gz 测试文件"""
    tar_path = os.path.join(tmp_dir, "test-project.tar.gz")
    _create_tar_gz(sample_project_dir, tar_path)
    return tar_path


@pytest.fixture
def sample_tar_bz2_file(sample_project_dir, tmp_dir):
    """创建一个 .tar.bz2 测试文件"""
    tar_path = os.path.join(tmp_dir, "test-project.tar.bz2")
    _create_tar_bz2(sample_project_dir, tar_path)
    return tar_path


@pytest.fixture
def path_traversal_zip(tmp_dir):
    """创建一个包含路径穿越的恶意 zip 文件"""
    zip_path = os.path.join(tmp_dir, "malicious.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../../etc/passwd", "root:x:0:0::/root:/bin/bash\n")
    return zip_path


@pytest.fixture
def zip_bomb_zip(tmp_dir):
    """创建一个模拟的 zip 炸弹（解压后体积远大于压缩前）"""
    zip_path = os.path.join(tmp_dir, "bomb.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        large_content = "A" * 1024 * 1024  # 1MB of 'A'
        for i in range(5):
            zf.writestr(f"huge_file_{i}.txt", large_content)
    return zip_path
