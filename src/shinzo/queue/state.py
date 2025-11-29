"""State management helpers for message state transitions."""

from datetime import datetime
from typing import Optional

from shinzo.models import QueuedMessage, MessageState
from shinzo.utils import get_logger


logger = get_logger(__name__)


def validate_state_transition(current: MessageState, new: MessageState) -> bool:
    """Validate if state transition is allowed."""
    valid_transitions = {
        MessageState.QUEUED: [MessageState.PROCESSING, MessageState.CANCELLED],
        MessageState.PROCESSING: [MessageState.COMPLETED, MessageState.FAILED],
        MessageState.COMPLETED: [],
        MessageState.FAILED: [],
        MessageState.CANCELLED: [],
    }
    return new in valid_transitions.get(current, [])


def update_message_timestamps(message: QueuedMessage, new_state: MessageState) -> None:
    """Update message timestamps based on state transition."""
    if new_state == MessageState.PROCESSING:
        message.started_at = datetime.utcnow()
    elif new_state in [MessageState.COMPLETED, MessageState.FAILED, MessageState.CANCELLED]:
        message.completed_at = datetime.utcnow()


def apply_state_change(
    message: QueuedMessage,
    new_state: MessageState,
    error: Optional[str],
    message_id: str,
    update_thread_state_counts,
) -> bool:
    """
    Apply state change to a message with validation and updates.
    
    Args:
        message: The message to update
        new_state: The new state
        error: Optional error message (for FAILED state)
        message_id: The message ID for logging
        update_thread_state_counts: Callback to update thread state counts
        
    Returns:
        True if change was applied successfully
    """
    old_state = message.state
    message.state = new_state
    update_message_timestamps(message, new_state)

    if new_state == MessageState.FAILED and error:
        message.error = error

    update_thread_state_counts(message, old_state, new_state)

    logger.info(
        f"Message state updated: id={message_id}, "
        f"from={old_state}, to={new_state}"
    )

    return True

