import asyncio
import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models import MessageState, SSEEvent
from app.queue_manager import QueueManager
from app.config import settings
from app.utils import get_logger


logger = get_logger(__name__)
router = APIRouter()

# This will be injected by the main app
queue_manager: Optional[QueueManager] = None


def set_queue_manager(qm: QueueManager):
    """Set the queue manager instance"""
    global queue_manager
    queue_manager = qm


async def generate_sse_events(message_id: str) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for a message

    Args:
        message_id: The message ID to stream

    Yields:
        SSE-formatted event strings
    """
    if not queue_manager:
        yield SSEEvent(
            event="error",
            data={"error": "Queue manager not initialized"}
        ).format()
        return

    # Get initial message state
    message = await queue_manager.get_message(message_id)

    if not message:
        yield SSEEvent(
            event="error",
            data={"error": f"Message not found: {message_id}"}
        ).format()
        return

    last_chunk_count = 0
    keepalive_counter = 0

    try:
        while True:
            # Refresh message state
            message = await queue_manager.get_message(message_id)

            if not message:
                yield SSEEvent(
                    event="error",
                    data={"error": "Message lost during streaming"}
                ).format()
                return

            # Handle different states
            if message.state == MessageState.QUEUED:
                # Send waiting status with queue position
                position = await queue_manager.get_queue_position(message_id)

                yield SSEEvent(
                    event="waiting",
                    data={
                        "state": "queued",
                        "position": position,
                        "message": "Waiting in queue",
                    }
                ).format()

                # Wait before checking again
                await asyncio.sleep(2.0)
                keepalive_counter += 2

            elif message.state == MessageState.PROCESSING:
                # Check if there are new chunks
                if len(message.chunks) > last_chunk_count:
                    # Send new chunks
                    for i in range(last_chunk_count, len(message.chunks)):
                        chunk = message.chunks[i]
                        yield SSEEvent(
                            event="chunk",
                            data={
                                "type": "content",
                                "chunk": chunk,
                                "index": i,
                            }
                        ).format()

                    last_chunk_count = len(message.chunks)
                    keepalive_counter = 0
                else:
                    # No new chunks, wait briefly
                    await asyncio.sleep(0.5)
                    keepalive_counter += 0.5

            elif message.state == MessageState.COMPLETED:
                # Send any remaining chunks
                if len(message.chunks) > last_chunk_count:
                    for i in range(last_chunk_count, len(message.chunks)):
                        chunk = message.chunks[i]
                        yield SSEEvent(
                            event="chunk",
                            data={
                                "type": "content",
                                "chunk": chunk,
                                "index": i,
                            }
                        ).format()

                # Send completion event
                yield SSEEvent(
                    event="done",
                    data={
                        "state": "completed",
                        "result": message.result or "",
                        "completed_at": message.completed_at.isoformat() if message.completed_at else None,
                    }
                ).format()

                logger.info(f"Stream completed for message: id={message_id}")
                return

            elif message.state == MessageState.FAILED:
                # Send error event
                yield SSEEvent(
                    event="error",
                    data={
                        "state": "failed",
                        "error": message.error or "Unknown error",
                        "completed_at": message.completed_at.isoformat() if message.completed_at else None,
                    }
                ).format()

                logger.info(f"Stream ended with error for message: id={message_id}")
                return

            elif message.state == MessageState.CANCELLED:
                # Send cancelled event
                yield SSEEvent(
                    event="cancelled",
                    data={
                        "state": "cancelled",
                        "message": "Message was cancelled",
                        "completed_at": message.completed_at.isoformat() if message.completed_at else None,
                    }
                ).format()

                logger.info(f"Stream ended (cancelled) for message: id={message_id}")
                return

            # Send keepalive if no activity
            if keepalive_counter >= settings.keepalive_interval:
                yield ": keepalive\n\n"
                keepalive_counter = 0

    except asyncio.CancelledError:
        logger.info(f"Stream cancelled for message: id={message_id}")
        raise

    except Exception as e:
        logger.error(f"Stream error for message {message_id}: {e}", exc_info=True)
        yield SSEEvent(
            event="error",
            data={"error": f"Streaming error: {str(e)}"}
        ).format()


@router.get("/messages/{message_id}/stream")
async def stream_message(message_id: str):
    """
    Stream message processing events via Server-Sent Events

    Args:
        message_id: The message ID to stream

    Returns:
        StreamingResponse with SSE events
    """
    if not queue_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue manager not initialized",
        )

    # Verify message exists
    message = await queue_manager.get_message(message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message not found: {message_id}",
        )

    logger.info(f"Starting SSE stream for message: id={message_id}, state={message.state}")

    # Return SSE streaming response
    return StreamingResponse(
        generate_sse_events(message_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
