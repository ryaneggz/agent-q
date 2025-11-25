import asyncio
from datetime import datetime
from typing import Optional, Dict
import logging

from app.models import (
    QueuedMessage,
    MessageState,
    Priority,
    PRIORITY_MAP,
    QueueSummaryResponse,
)


logger = logging.getLogger(__name__)


class QueueManager:
    """Manages the in-memory message queue with priority support"""

    def __init__(self):
        # Priority queue for message processing
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

        # Dictionary to store message metadata by ID
        self._messages: Dict[str, QueuedMessage] = {}

        # Lock for thread-safe state transitions
        self._lock = asyncio.Lock()

        # Event to signal when new messages are added
        self._new_message_event = asyncio.Event()

        # Counter for insertion order (FIFO within same priority)
        self._counter = 0

    async def enqueue(self, user_message: str, priority: Priority = Priority.NORMAL) -> QueuedMessage:
        """
        Add a message to the queue

        Args:
            user_message: The user's message text
            priority: Message priority level

        Returns:
            The created QueuedMessage object
        """
        async with self._lock:
            # Create message object
            message = QueuedMessage(
                user_message=user_message,
                priority=priority,
                state=MessageState.QUEUED,
            )

            # Store message metadata
            self._messages[message.id] = message

            # Add to priority queue
            # Priority queue uses (priority, counter) tuple for ordering
            # Lower priority number = higher priority
            # Counter ensures FIFO within same priority
            priority_value = PRIORITY_MAP[priority]
            await self._queue.put((priority_value, self._counter, message.id))
            self._counter += 1

            logger.info(
                f"Message enqueued: id={message.id}, priority={priority}, "
                f"queue_size={self._queue.qsize()}"
            )

            # Signal that a new message is available
            self._new_message_event.set()

            return message

    async def dequeue(self) -> Optional[QueuedMessage]:
        """
        Remove and return the next message from the queue

        Returns:
            The next QueuedMessage or None if queue is empty
        """
        try:
            # Get next message (non-blocking)
            _, _, message_id = await self._queue.get()

            async with self._lock:
                message = self._messages.get(message_id)

                if message and message.state == MessageState.QUEUED:
                    # Update state to processing
                    message.state = MessageState.PROCESSING
                    message.started_at = datetime.utcnow()

                    logger.info(f"Message dequeued: id={message.id}")
                    return message
                elif message and message.state == MessageState.CANCELLED:
                    # Message was cancelled, skip it
                    logger.info(f"Skipping cancelled message: id={message.id}")
                    return None
                else:
                    logger.warning(f"Message not found or invalid state: id={message_id}")
                    return None

        except asyncio.QueueEmpty:
            return None

    async def update_state(
        self, message_id: str, new_state: MessageState, error: Optional[str] = None
    ) -> bool:
        """
        Update the state of a message

        Args:
            message_id: The message ID
            new_state: The new state
            error: Optional error message (for FAILED state)

        Returns:
            True if update was successful, False otherwise
        """
        async with self._lock:
            message = self._messages.get(message_id)

            if not message:
                logger.warning(f"Message not found for state update: id={message_id}")
                return False

            # Validate state transition
            if not self._is_valid_transition(message.state, new_state):
                logger.warning(
                    f"Invalid state transition: id={message_id}, "
                    f"from={message.state}, to={new_state}"
                )
                return False

            # Update state
            old_state = message.state
            message.state = new_state

            # Update timestamps
            if new_state == MessageState.PROCESSING:
                message.started_at = datetime.utcnow()
            elif new_state in [MessageState.COMPLETED, MessageState.FAILED, MessageState.CANCELLED]:
                message.completed_at = datetime.utcnow()

            # Store error if provided
            if new_state == MessageState.FAILED and error:
                message.error = error

            logger.info(
                f"Message state updated: id={message_id}, "
                f"from={old_state}, to={new_state}"
            )

            return True

    def _is_valid_transition(self, current: MessageState, new: MessageState) -> bool:
        """Validate if state transition is allowed"""
        valid_transitions = {
            MessageState.QUEUED: [MessageState.PROCESSING, MessageState.CANCELLED],
            MessageState.PROCESSING: [MessageState.COMPLETED, MessageState.FAILED],
            MessageState.COMPLETED: [],
            MessageState.FAILED: [],
            MessageState.CANCELLED: [],
        }

        return new in valid_transitions.get(current, [])

    async def get_message(self, message_id: str) -> Optional[QueuedMessage]:
        """
        Get a message by ID

        Args:
            message_id: The message ID

        Returns:
            The QueuedMessage or None if not found
        """
        async with self._lock:
            return self._messages.get(message_id)

    async def cancel_message(self, message_id: str) -> tuple[bool, Optional[str]]:
        """
        Cancel a message if it's still queued

        Args:
            message_id: The message ID

        Returns:
            Tuple of (success, error_message)
        """
        async with self._lock:
            message = self._messages.get(message_id)

            if not message:
                return False, "Message not found"

            if message.state != MessageState.QUEUED:
                return False, f"Cannot cancel message in state: {message.state}"

            # Update state to cancelled
            message.state = MessageState.CANCELLED
            message.completed_at = datetime.utcnow()

            logger.info(f"Message cancelled: id={message_id}")

            return True, None

    async def set_result(self, message_id: str, result: str) -> bool:
        """
        Set the result for a completed message

        Args:
            message_id: The message ID
            result: The agent result text

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            message = self._messages.get(message_id)

            if not message:
                return False

            message.result = result
            return True

    async def add_chunk(self, message_id: str, chunk: str) -> bool:
        """
        Add a streaming chunk to a message

        Args:
            message_id: The message ID
            chunk: The chunk text

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            message = self._messages.get(message_id)

            if not message:
                return False

            message.chunks.append(chunk)
            return True

    async def get_queue_position(self, message_id: str) -> Optional[int]:
        """
        Get the queue position of a message

        Args:
            message_id: The message ID

        Returns:
            Queue position (0-indexed) or None if not in queue
        """
        async with self._lock:
            message = self._messages.get(message_id)

            if not message or message.state != MessageState.QUEUED:
                return None

            # Count messages with higher or equal priority that are queued
            position = 0
            message_priority = PRIORITY_MAP[message.priority]

            # This is a simplified position calculation
            # In practice, we'd need to iterate through the queue
            for msg in self._messages.values():
                if msg.state == MessageState.QUEUED and msg.id != message_id:
                    msg_priority = PRIORITY_MAP[msg.priority]
                    if (msg_priority < message_priority) or (
                        msg_priority == message_priority and msg.created_at < message.created_at
                    ):
                        position += 1

            return position

    async def get_queue_summary(self) -> QueueSummaryResponse:
        """
        Get a summary of the queue state

        Returns:
            QueueSummaryResponse object
        """
        async with self._lock:
            # Count messages by state
            state_counts = {state: 0 for state in MessageState}

            for message in self._messages.values():
                state_counts[message.state] += 1

            # Get queued messages
            queued_messages = [
                {
                    "id": msg.id,
                    "priority": msg.priority.value,
                    "created_at": msg.created_at.isoformat(),
                    "user_message": msg.user_message[:100],  # Truncate for display
                }
                for msg in self._messages.values()
                if msg.state == MessageState.QUEUED
            ]

            # Sort by priority and creation time
            queued_messages.sort(
                key=lambda x: (
                    PRIORITY_MAP[Priority(x["priority"])],
                    x["created_at"],
                )
            )

            # Get currently processing message
            processing_messages = [
                {
                    "id": msg.id,
                    "priority": msg.priority.value,
                    "started_at": msg.started_at.isoformat() if msg.started_at else None,
                    "user_message": msg.user_message[:100],
                }
                for msg in self._messages.values()
                if msg.state == MessageState.PROCESSING
            ]

            current_processing = processing_messages[0] if processing_messages else None

            return QueueSummaryResponse(
                total_queued=state_counts[MessageState.QUEUED],
                total_processing=state_counts[MessageState.PROCESSING],
                total_completed=state_counts[MessageState.COMPLETED],
                total_failed=state_counts[MessageState.FAILED],
                total_cancelled=state_counts[MessageState.CANCELLED],
                queued_messages=queued_messages,
                current_processing=current_processing,
            )

    async def wait_for_messages(self):
        """Wait until a new message is added to the queue"""
        await self._new_message_event.wait()
        self._new_message_event.clear()

    def has_messages(self) -> bool:
        """Check if there are messages in the queue"""
        return not self._queue.empty()
