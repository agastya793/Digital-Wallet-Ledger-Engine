import json
import logging
from typing import Any

from app.cache.core import redis_client

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def publish_transaction_event(
        user_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """
        Publishes a transaction event to the user's specific Redis channel.

        Args:
            user_id: The UUID of the user receiving the notification.
            event_type: 'transaction_started', 'transaction_completed', 'transaction_failed'
            payload: Relevant data (amount, status, transaction_id, etc)
        """
        channel = f"notifications:user:{user_id}"
        message = {"type": event_type, "data": payload}

        try:
            await redis_client.publish(channel, json.dumps(message))
            logger.debug(f"Published event {event_type} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish notification to {channel}: {e}")
