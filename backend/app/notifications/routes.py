import asyncio
import logging

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.cache.core import redis_client
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_id_from_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)) -> None:
    await websocket.accept()

    user_id = await get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token")
        return

    channel_name = f"notifications:user:{user_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name)

    logger.info(f"WebSocket connected for user {user_id}")

    try:
        while True:
            # We need to both listen to the websocket (so we can detect disconnects)
            # and listen to redis pubsub.

            # Create a task to read from pubsub
            async def read_pubsub() -> str:
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message["type"] == "message":
                        return message["data"].decode("utf-8")
                    await asyncio.sleep(0.1)

            # Wait for either a websocket receive (which means client disconnected or sent something)
            # or a pubsub message.
            receive_task = asyncio.create_task(websocket.receive_text())
            pubsub_task = asyncio.create_task(read_pubsub())

            done, pending = await asyncio.wait(
                [receive_task, pubsub_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if receive_task in done:
                # Client disconnected or sent a message (we ignore messages from client, but catch disconnects)
                break

            if pubsub_task in done:
                # We got a pubsub message
                msg = pubsub_task.result()
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(msg)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
