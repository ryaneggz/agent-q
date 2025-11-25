import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.models import (
    MessageState,
    MessageStatusResponse,
    ThreadMetadata,
    ThreadMessagesResponse,
    ThreadSummary,
)
from app.queue_manager import QueueManager


logger = logging.getLogger(__name__)
router = APIRouter()

# This will be injected by the main app
queue_manager: Optional[QueueManager] = None


def set_queue_manager(qm: QueueManager):
    """Set the queue manager instance"""
    global queue_manager
    queue_manager = qm


async def _ensure_queue_manager() -> QueueManager:
    if not queue_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue manager not initialized",
        )
    return queue_manager


async def _message_to_status(message, qm: QueueManager) -> MessageStatusResponse:
    queue_position = None
    if message.state == MessageState.QUEUED:
        queue_position = await qm.get_queue_position(message.id)

    return MessageStatusResponse(
        message_id=message.id,
        state=message.state,
        user_message=message.user_message,
        priority=message.priority,
        created_at=message.created_at,
        started_at=message.started_at,
        completed_at=message.completed_at,
        result=message.result,
        error=message.error,
        queue_position=queue_position,
        thread_id=message.thread_id,
    )


@router.get("/threads", response_model=list[ThreadSummary])
async def list_threads():
    """
    List all threads with summary information ordered by last activity
    """
    qm = await _ensure_queue_manager()
    summaries = await qm.list_threads()
    logger.info("Retrieved %s threads", len(summaries))
    return summaries


@router.get("/threads/{thread_id}/messages", response_model=ThreadMessagesResponse)
async def get_thread_messages(thread_id: str):
    """
    Retrieve all messages for a specific thread in chronological order
    """
    qm = await _ensure_queue_manager()

    metadata = await qm.get_thread_metadata(thread_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread not found: {thread_id}",
        )

    messages = await qm.get_thread_messages(thread_id)
    message_responses = [
        await _message_to_status(message, qm) for message in messages
    ]

    return ThreadMessagesResponse(
        thread_id=thread_id,
        total_messages=len(message_responses),
        messages=message_responses,
    )


@router.get("/threads/{thread_id}", response_model=ThreadMetadata)
async def get_thread_metadata(thread_id: str):
    """
    Retrieve metadata for a specific thread
    """
    qm = await _ensure_queue_manager()
    metadata = await qm.get_thread_metadata(thread_id)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread not found: {thread_id}",
        )

    return metadata

