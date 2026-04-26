import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ReviewProgressConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time review progress updates."""

    group_name: str

    async def connect(self) -> None:
        review_id = self.scope["url_route"]["kwargs"]["review_id"]
        self.group_name = f"review_progress_{review_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WebSocket connected for review %s", review_id)

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WebSocket disconnected (code=%s)", code)

    async def review_progress(self, event: dict) -> None:
        """Handle progress messages from the channel layer."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "review_progress",
                    "progress": event["progress"],
                    "status": event["status"],
                    "message": event.get("message", ""),
                }
            )
        )
