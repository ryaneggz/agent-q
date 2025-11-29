"""Queue operations helpers for enqueue/dequeue operations."""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from shinzo.models import QueuedMessage, MessageState, Priority, PRIORITY_MAP
from shinzo.utils import get_logger


logger = get_logger(__name__)


def create_message(
    user_message: str, thread_id: str, priority: Priority
) -> QueuedMessage:
    """Create a new QueuedMessage object."""
    return QueuedMessage(
        user_message=user_message,
        priority=priority,
        state=MessageState.QUEUED,
        thread_id=thread_id,
    )


def ensure_thread_resources(
    thread_id: str,
    thread_queues: Dict[str, asyncio.PriorityQueue],
    thread_events: Dict[str, asyncio.Event],
) -> None:
    """Ensure thread has a queue and event initialized."""
    if thread_id not in thread_queues:
        thread_queues[thread_id] = asyncio.PriorityQueue()
        thread_events[thread_id] = asyncio.Event()


async def add_message_to_queue(
    thread_id: str,
    priority: Priority,
    message_id: str,
    thread_queues: Dict[str, asyncio.PriorityQueue],
    insertion_order_counter: int,
) -> int:
    """
    Add message to thread's priority queue.
    
    Returns:
        Updated insertion_order_counter
    """
    priority_value = PRIORITY_MAP[priority]
    await thread_queues[thread_id].put(
        (priority_value, insertion_order_counter, message_id)
    )
    return insertion_order_counter + 1


def log_message_enqueued(
    message: QueuedMessage,
    thread_id: str,
    thread_queues: Dict[str, asyncio.PriorityQueue],
) -> None:
    """Log message enqueue operation."""
    queue_size = thread_queues[thread_id].qsize()
    logger.info(
        f"Message enqueued: id={message.id}, thread_id={thread_id}, "
        f"priority={message.priority}, thread_queue_size={queue_size}"
    )


def signal_thread_message_available(
    thread_id: str, thread_events: Dict[str, asyncio.Event]
) -> None:
    """Signal that a new message is available for a thread."""
    thread_events[thread_id].set()


async def process_dequeued_message(
    thread_id: str,
    thread_queue: asyncio.PriorityQueue,
    message_id: str,
    messages: Dict[str, QueuedMessage],
    active_threads: set,
    lock: asyncio.Lock,
    update_thread_state_counts,
) -> Optional[QueuedMessage]:
    """Process a dequeued message and return it if valid."""
    async with lock:
        message = messages.get(message_id)

        if message and message.state == MessageState.QUEUED:
            return handle_valid_dequeued_message(
                thread_id, thread_queue, message, active_threads, update_thread_state_counts
            )
        elif message and message.state == MessageState.CANCELLED:
            return handle_cancelled_message(thread_id, thread_queue, message, active_threads)
        else:
            logger.warning(f"Message not found or invalid state: id={message_id}")
            return None


def handle_valid_dequeued_message(
    thread_id: str,
    thread_queue: asyncio.PriorityQueue,
    message: QueuedMessage,
    active_threads: set,
    update_thread_state_counts,
) -> QueuedMessage:
    """Handle a valid dequeued message by updating its state."""
    message.state = MessageState.PROCESSING
    message.started_at = datetime.utcnow()
    update_thread_state_counts(
        message, MessageState.QUEUED, MessageState.PROCESSING
    )

    if thread_queue.empty():
        active_threads.discard(thread_id)

    logger.info(f"Message dequeued: id={message.id}, thread_id={thread_id}")
    return message


def handle_cancelled_message(
    thread_id: str,
    thread_queue: asyncio.PriorityQueue,
    message: QueuedMessage,
    active_threads: set,
) -> Optional[QueuedMessage]:
    """Handle a cancelled message by skipping it."""
    logger.info(f"Skipping cancelled message: id={message.id}")
    
    if thread_queue.empty():
        active_threads.discard(thread_id)
    
    return None

