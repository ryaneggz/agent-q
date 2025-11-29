"""Queue summary building helpers."""

from typing import Dict, List, Optional

from shinzo.models import (
    QueuedMessage,
    MessageState,
    Priority,
    PRIORITY_MAP,
)


def calculate_message_priority_value(priority: Priority) -> int:
    """Calculate the numeric priority value for a message."""
    return PRIORITY_MAP[priority]


def count_higher_priority_messages(
    message_id: str,
    message_priority_value: int,
    message_created_at,
    messages: Dict[str, QueuedMessage],
) -> int:
    """Count messages with higher or equal priority that were created earlier."""
    position = 0
    for msg in messages.values():
        if msg.state == MessageState.QUEUED and msg.id != message_id:
            msg_priority_value = PRIORITY_MAP[msg.priority]
            if (msg_priority_value < message_priority_value) or (
                msg_priority_value == message_priority_value and msg.created_at < message_created_at
            ):
                position += 1
    return position


def count_messages_by_state(messages: Dict[str, QueuedMessage]) -> Dict[MessageState, int]:
    """Count messages by their current state."""
    state_counts = {state: 0 for state in MessageState}
    for message in messages.values():
        state_counts[message.state] += 1
    return state_counts


def build_queued_message_list(messages: Dict[str, QueuedMessage]) -> List[dict]:
    """Build a list of queued message dictionaries for summary."""
    queued_messages = [
        build_queued_message_dict(msg)
        for msg in messages.values()
        if msg.state == MessageState.QUEUED
    ]

    queued_messages.sort(
        key=lambda x: (
            PRIORITY_MAP[Priority(x["priority"])],
            x["created_at"],
        )
    )
    return queued_messages


def build_queued_message_dict(message: QueuedMessage) -> dict:
    """Build a dictionary representation of a queued message."""
    return {
        "id": message.id,
        "priority": message.priority.value,
        "created_at": message.created_at.isoformat(),
        "user_message": message.user_message[:100],  # Truncate for display
    }


def build_current_processing_message(messages: Dict[str, QueuedMessage]) -> Optional[dict]:
    """Build dictionary for currently processing message."""
    processing_messages = [
        build_processing_message_dict(msg)
        for msg in messages.values()
        if msg.state == MessageState.PROCESSING
    ]
    return processing_messages[0] if processing_messages else None


def build_processing_message_dict(message: QueuedMessage) -> dict:
    """Build a dictionary representation of a processing message."""
    return {
        "id": message.id,
        "priority": message.priority.value,
        "started_at": message.started_at.isoformat() if message.started_at else None,
        "user_message": message.user_message[:100],
    }

