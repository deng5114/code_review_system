import io
import os
import zipfile

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def sample_zip_upload(tmp_dir):
    """创建一个可上传的 zip 文件"""
    zip_buffer = io.BytesIO()
    project_dir = os.path.join(tmp_dir, "upload-test-project")
    os.makedirs(project_dir)

    with open(os.path.join(project_dir, "main.py"), "w") as f:
        f.write("print('hello world')\n\ndef add(a, b):\n    return a + b\n")

    with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
        f.write("django>=5.0\n")

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tmp_dir)
                zf.write(file_path, arcname)

    zip_buffer.seek(0)
    zip_buffer.name = "test-project.zip"
    return zip_buffer


@pytest.mark.django_db
class TestProjectUpload:
    """项目上传 API 集成测试"""

    def test_upload_zip_success(self, auth_client, sample_zip_upload):
        response = auth_client.post(
            "/api/projects/",
            {"name": "测试项目", "file": sample_zip_upload},
            format="multipart",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "测试项目"
        assert data["data"]["status"] == "ready"
        assert data["data"]["project_type"] == "python"

    def test_upload_sets_project_type(self, auth_client, sample_zip_upload):
        response = auth_client.post(
            "/api/projects/",
            {"name": "类型检测", "file": sample_zip_upload},
            format="multipart",
        )
        data = response.json()
        assert data["data"]["project_type"] == "python"

    def test_upload_detects_languages(self, auth_client, sample_zip_upload):
        response = auth_client.post(
            "/api/projects/",
            {"name": "语言检测", "file": sample_zip_upload},
            format="multipart",
        )
        data = response.json()
        assert "python" in data["data"]["detected_languages"]

    def test_upload_creates_project_files(self, auth_client, sample_zip_upload):
        response = auth_client.post(
            "/api/projects/",
            {"name": "文件记录", "file": sample_zip_upload},
            format="multipart",
        )
        project_id = response.json()["data"]["id"]
        files_resp = auth_client.get(f"/api/projects/{project_id}/files/")
        assert files_resp.status_code == 200
        files_data = files_resp.json()["data"]
        assert len(files_data) > 0

    def test_upload_missing_name(self, auth_client, sample_zip_upload):
        response = auth_client.post(
            "/api/projects/",
            {"file": sample_zip_upload},
            format="multipart",
        )
        assert response.status_code == 400

    def test_upload_missing_file(self, auth_client):
        response = auth_client.post(
            "/api/projects/",
            {"name": "无文件"},
            format="multipart",
        )
        assert response.status_code == 400

    def test_unauthenticated_upload(self, api_client, sample_zip_upload):
        response = api_client.post(
            "/api/projects/",
            {"name": "未认证", "file": sample_zip_upload},
            format="multipart",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestProjectList:
    """项目列表 API 测试"""

    def test_list_projects_empty(self, auth_client):
        response = auth_client.get("/api/projects/")
        assert response.status_code == 200

    def test_list_projects_after_upload(self, auth_client, sample_zip_upload):
        auth_client.post(
            "/api/projects/",
            {"name": "列表测试", "file": sample_zip_upload},
            format="multipart",
        )
        response = auth_client.get("/api/projects/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestProjectDetail:
    """项目详情 API 测试"""

    def test_get_project_detail(self, auth_client, sample_zip_upload):
        resp = auth_client.post(
            "/api/projects/",
            {"name": "详情测试", "file": sample_zip_upload},
            format="multipart",
        )
        project_id = resp.json()["data"]["id"]
        response = auth_client.get(f"/api/projects/{project_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "详情测试"

    def test_get_nonexistent_project(self, auth_client):
        response = auth_client.get("/api/projects/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestProjectFiles:
    """项目文件 API 测试"""

    def test_get_file_content(self, auth_client, sample_zip_upload):
        resp = auth_client.post(
            "/api/projects/",
            {"name": "文件内容", "file": sample_zip_upload},
            format="multipart",
        )
        project_id = resp.json()["data"]["id"]

        files_resp = auth_client.get(f"/api/projects/{project_id}/files/")
        file_id = files_resp.json()["data"][0]["id"]

        content_resp = auth_client.get(f"/api/projects/{project_id}/files/{file_id}/")
        assert content_resp.status_code == 200
        content_data = content_resp.json()["data"]
        assert "content" in content_data
        assert "language" in content_data

    def test_get_nonexistent_file(self, auth_client, sample_zip_upload):
        resp = auth_client.post(
            "/api/projects/",
            {"name": "不存在文件", "file": sample_zip_upload},
            format="multipart",
        )
        project_id = resp.json()["data"]["id"]
        response = auth_client.get(
            f"/api/projects/{project_id}/files/00000000-0000-0000-0000-000000000000/"
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestProjectDelete:
    """项目删除 API 测试"""

    def test_delete_project(self, auth_client, sample_zip_upload):
        resp = auth_client.post(
            "/api/projects/",
            {"name": "删除测试", "file": sample_zip_upload},
            format="multipart",
        )
        project_id = resp.json()["data"]["id"]
        response = auth_client.delete(f"/api/projects/{project_id}/")
        assert response.status_code == 200
