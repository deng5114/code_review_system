from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.testing import WebsocketCommunicator

from apps.projects.models import Project
from apps.reviews.consumers import ReviewProgressConsumer
from apps.reviews.models import Review, ReviewStatus


@pytest.fixture
def review_with_project(db, user):
    project = Project.objects.create(
        name="WSProject",
        owner=user,
        status="ready",
        project_type="python",
    )
    review = Review.objects.create(
        project=project,
        status=ReviewStatus.RUNNING,
        ai_model="gpt-4o",
        ai_provider="openai",
    )
    return review


def _make_communicator(review_id: str) -> WebsocketCommunicator:
    """Create a WebsocketCommunicator wired directly to the consumer."""
    app = ReviewProgressConsumer.as_asgi()
    communicator = WebsocketCommunicator(app, f"/ws/reviews/{review_id}/progress/")
    communicator.scope["url_route"] = {"kwargs": {"review_id": review_id}}
    return communicator


@pytest.mark.django_db(transaction=True)
class TestReviewProgressConsumer:
    async def test_connect_success(self, review_with_project):
        communicator = _make_communicator(str(review_with_project.id))
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_connect_nonexistent_review(self, db):
        communicator = _make_communicator("00000000-0000-0000-0000-000000000000")
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_receive_progress_message(self, review_with_project):
        communicator = _make_communicator(str(review_with_project.id))
        connected, _ = await communicator.connect()
        assert connected

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"review_progress_{review_with_project.id}",
            {
                "type": "review_progress",
                "progress": 50,
                "status": "running",
                "message": "Reviewing chunk 3/7...",
            },
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "review_progress"
        assert response["progress"] == 50
        assert response["status"] == "running"
        assert "chunk 3/7" in response["message"]

        await communicator.disconnect()

    async def test_completed_message(self, review_with_project):
        communicator = _make_communicator(str(review_with_project.id))
        connected, _ = await communicator.connect()
        assert connected

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"review_progress_{review_with_project.id}",
            {
                "type": "review_progress",
                "progress": 100,
                "status": "completed",
                "message": "Review completed",
            },
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response["status"] == "completed"
        assert response["progress"] == 100

        await communicator.disconnect()

    async def test_failed_message(self, review_with_project):
        communicator = _make_communicator(str(review_with_project.id))
        connected, _ = await communicator.connect()
        assert connected

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"review_progress_{review_with_project.id}",
            {
                "type": "review_progress",
                "progress": 0,
                "status": "failed",
                "message": "API timeout",
            },
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response["status"] == "failed"
        assert response["progress"] == 0
        assert "timeout" in response["message"].lower()

        await communicator.disconnect()

    async def test_disconnect_leaves_group(self, review_with_project):
        communicator = _make_communicator(str(review_with_project.id))
        connected, _ = await communicator.connect()
        assert connected

        await communicator.disconnect()

        # After disconnect, messages to the group should not be received
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"review_progress_{review_with_project.id}",
            {
                "type": "review_progress",
                "progress": 99,
                "status": "running",
                "message": "Should not arrive",
            },
        )

        # No message should be waiting
        nothing = await communicator.receive_nothing(timeout=1)
        assert nothing is True


@pytest.mark.django_db
class TestPushProgress:
    """Test the _push_progress helper used by Celery tasks."""

    def test_push_progress_success(self, review_with_project):
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()

        with patch("apps.reviews.tasks.get_channel_layer", return_value=mock_layer):
            from apps.reviews.tasks import _push_progress

            _push_progress(str(review_with_project.id), 75, "running", "Almost done")

        mock_layer.group_send.assert_called_once()
        call_args = mock_layer.group_send.call_args
        assert call_args[0][0] == f"review_progress_{review_with_project.id}"
        msg = call_args[0][1]
        assert msg["progress"] == 75
        assert msg["status"] == "running"

    def test_push_progress_no_channel_layer(self, review_with_project):
        with patch("apps.reviews.tasks.get_channel_layer", return_value=None):
            from apps.reviews.tasks import _push_progress

            _push_progress(str(review_with_project.id), 50, "running")

    def test_push_progress_exception_handled(self, review_with_project):
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock(side_effect=Exception("Redis down"))

        with patch("apps.reviews.tasks.get_channel_layer", return_value=mock_layer):
            from apps.reviews.tasks import _push_progress

            _push_progress(str(review_with_project.id), 50, "running")
