import pytest


@pytest.fixture(autouse=True)
def use_in_memory_channel_layer():
    """Use InMemoryChannelLayer in all tests to avoid Redis dependency."""
    from django.conf import settings

    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
