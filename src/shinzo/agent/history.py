"""Conversation history building for thread-based messages."""

from typing import List, Tuple

from shinzo.models import QueuedMessage, MessageState
from shinzo.queue import QueueManager
from shinzo.utils import get_logger


logger = get_logger(__name__)


async def build_conversation_history(
    message: QueuedMessage, queue_manager: QueueManager
) -> List[Tuple[str, str]]:
    """
    Build conversation history for a message, including thread context.

    Args:
        message: The current message to process
        queue_manager: Queue manager to retrieve thread messages

    Returns:
        List of (role, content) tuples representing conversation history
    """
    messages = []

    if message.thread_id:
        # Get all previous messages in the thread (chronologically)
        thread_messages = await queue_manager.get_thread_messages(message.thread_id)

        # Add previous messages to conversation history
        for prev_msg in thread_messages:
            # Skip the current message (it will be added last)
            if prev_msg.id == message.id:
                continue

            # Add user message
            messages.append(("user", prev_msg.user_message))

            # Add assistant response if completed
            if prev_msg.result and prev_msg.state == MessageState.COMPLETED:
                messages.append(("assistant", prev_msg.result))

    # Add current user message last
    messages.append(("user", message.user_message))

    logger.info(
        f"Built conversation history with {len(messages)} messages "
        f"(thread_id={message.thread_id})"
    )

    return messages

