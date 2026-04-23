from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.models import AIConfig


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_config(db):
    config = AIConfig(
        provider="openai",
        display_name="Test OpenAI",
        model_name="gpt-4o",
        base_url="",
        is_default=True,
        is_active=True,
        extra_settings={},
    )
    config.api_key = "sk-test-api-key-123"
    config.save()
    return config


@pytest.mark.django_db
class TestAIConfigCRUD:
    def test_create_config(self, api_client):
        data = {
            "provider": "openai",
            "display_name": "My OpenAI",
            "model_name": "gpt-4o",
            "api_key": "sk-brand-new-key-here",
            "base_url": "",
            "is_default": True,
        }
        resp = api_client.post("/api/ai/configs/", data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["success"] is True
        assert resp.data["data"]["provider"] == "openai"
        assert resp.data["data"]["model_name"] == "gpt-4o"
        assert "api_key" not in resp.data["data"]
        assert resp.data["data"]["masked_api_key"]

    def test_list_configs(self, api_client, sample_config):
        resp = api_client.get("/api/ai/configs/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        assert len(resp.data["data"]) >= 1

    def test_retrieve_config(self, api_client, sample_config):
        resp = api_client.get(f"/api/ai/configs/{sample_config.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["display_name"] == "Test OpenAI"
        assert "masked_api_key" in resp.data["data"]
        assert "api_key" not in resp.data["data"]

    def test_update_config(self, api_client, sample_config):
        data = {
            "display_name": "Updated Name",
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "api_key": "sk-updated-key-here",
            "base_url": "",
        }
        resp = api_client.put(
            f"/api/ai/configs/{sample_config.id}/", data, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["display_name"] == "Updated Name"
        assert resp.data["data"]["model_name"] == "gpt-4o-mini"

    def test_partial_update_config(self, api_client, sample_config):
        resp = api_client.patch(
            f"/api/ai/configs/{sample_config.id}/",
            {"display_name": "Partial Update"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["display_name"] == "Partial Update"

    def test_delete_config(self, api_client, sample_config):
        resp = api_client.delete(f"/api/ai/configs/{sample_config.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not AIConfig.objects.filter(id=sample_config.id).exists()

    def test_create_config_short_api_key(self, api_client):
        data = {
            "provider": "openai",
            "display_name": "Bad Key",
            "model_name": "gpt-4o",
            "api_key": "short",
            "base_url": "",
        }
        resp = api_client.post("/api/ai/configs/", data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_api_key_not_returned_in_response(self, api_client, sample_config):
        resp = api_client.get(f"/api/ai/configs/{sample_config.id}/")
        data = resp.data["data"]
        assert "api_key" not in data
        assert data["masked_api_key"].endswith("123")


@pytest.mark.django_db
class TestTestConnection:
    @patch("apps.ai.views.LLMAdapter.chat_completion")
    def test_connection_with_config_id(self, mock_completion, api_client, sample_config):
        from apps.ai.services.llm_adapter import LLMResult

        mock_completion.return_value = LLMResult(
            content="ok", total_tokens=10, prompt_tokens=5, completion_tokens=5
        )
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {"config_id": str(sample_config.id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["connected"] is True

    @patch("apps.ai.views.LLMAdapter.chat_completion")
    def test_connection_with_explicit_params(self, mock_completion, api_client):
        from apps.ai.services.llm_adapter import LLMResult

        mock_completion.return_value = LLMResult(
            content="ok", total_tokens=8, prompt_tokens=4, completion_tokens=4
        )
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {
                "provider": "anthropic",
                "model_name": "claude-sonnet-4-20250514",
                "api_key": "sk-ant-test-key-here",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["connected"] is True

    @patch("apps.ai.views.LLMAdapter.chat_completion")
    def test_connection_failure(self, mock_completion, api_client, sample_config):
        from apps.ai.services.llm_adapter import LLMCallError

        mock_completion.side_effect = LLMCallError("连接失败")
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {"config_id": str(sample_config.id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["connected"] is False

    def test_connection_missing_params(self, api_client):
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_connection_nonexistent_config(self, api_client):
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {"config_id": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_connection_blocks_private_url(self, api_client):
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {
                "provider": "openai",
                "model_name": "gpt-4o",
                "api_key": "sk-test-key-here12345",
                "base_url": "http://169.254.169.254/latest/meta-data/",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"]["code"] == "BLOCKED_URL"

    def test_connection_blocks_localhost(self, api_client):
        resp = api_client.post(
            "/api/ai/configs/test-connection/",
            {
                "provider": "openai",
                "model_name": "gpt-4o",
                "api_key": "sk-test-key-here12345",
                "base_url": "http://localhost:8080",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
