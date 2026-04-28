import pytest
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client(api_client, user) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client
