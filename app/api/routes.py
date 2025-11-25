from fastapi import APIRouter, HTTPException, status
from typing import Optional
import logging

from app.models import (
    MessageSubmitRequest,
    MessageSubmitResponse,
    MessageStatusResponse,
    QueueSummaryResponse,
    MessageState,
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


@router.post("/messages", response_model=MessageSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_message(request: MessageSubmitRequest):
    """
    Submit a new message to the queue

    Args:
        request: Message submission request

    Returns:
        MessageSubmitResponse with message ID and queue position
    """
    if not queue_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue manager not initialized",
        )

    try:
        # Enqueue the message
        message = await queue_manager.enqueue(
            user_message=request.message,
            priority=request.priority,
            thread_id=request.thread_id,
        )

        # Get queue position
        queue_position = await queue_manager.get_queue_position(message.id)

        logger.info(
            f"Message submitted: id={message.id}, priority={request.priority}, "
            f"position={queue_position}"
        )

        return MessageSubmitResponse(
            message_id=message.id,
            state=message.state,
            queue_position=queue_position,
            created_at=message.created_at,
            thread_id=message.thread_id,
        )

    except Exception as e:
        logger.error(f"Error submitting message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit message",
        )


@router.get("/messages/{message_id}/status", response_model=MessageStatusResponse)
async def get_message_status(message_id: str):
    """
    Get the status of a message

    Args:
        message_id: The message ID

    Returns:
        MessageStatusResponse with current state and details
    """
    if not queue_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue manager not initialized",
        )

    message = await queue_manager.get_message(message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message not found: {message_id}",
        )

    # Get queue position if still queued
    queue_position = None
    if message.state == MessageState.QUEUED:
        queue_position = await queue_manager.get_queue_position(message_id)

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


@router.delete("/messages/{message_id}", status_code=status.HTTP_200_OK)
async def cancel_message(message_id: str):
    """
    Cancel a queued message

    Args:
        message_id: The message ID

    Returns:
        Success message
    """
    if not queue_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue manager not initialized",
        )

    success, error = await queue_manager.cancel_message(message_id)

    if not success:
        if error == "Message not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error,
            )

    logger.info(f"Message cancelled via API: id={message_id}")

    return {"message": "Message cancelled successfully", "message_id": message_id}


@router.get("/queue", response_model=QueueSummaryResponse)
async def get_queue_summary():
    """
    Get a summary of the queue state

    Returns:
        QueueSummaryResponse with queue statistics
    """
    if not queue_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue manager not initialized",
        )

    summary = await queue_manager.get_queue_summary()
    return summary


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "queue_initialized": queue_manager is not None,
    }
