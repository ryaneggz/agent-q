"""Main QueueManager class for managing message queues."""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Set, List

from shinzo.models import (
    QueuedMessage,
    MessageState,
    Priority,
    QueueSummaryResponse,
    ThreadMetadata,
    ThreadSummary,
)
from shinzo.queue.types import CancelResult
from shinzo.queue import state
from shinzo.queue import threads
from shinzo.queue import operations
from shinzo.queue import summary
from shinzo.utils import get_logger


logger = get_logger(__name__)


class QueueManager:
    """Manages the in-memory message queue with priority support"""

    def __init__(self):
        # Per-thread priority queues for message processing
        self._thread_queues: Dict[str, asyncio.PriorityQueue] = {}

        # Dictionary to store message metadata by ID
        self._messages: Dict[str, QueuedMessage] = {}

        # Lock for thread-safe state transitions
        self._lock = asyncio.Lock()

        # Per-thread events to signal when new messages are added
        self._thread_events: Dict[str, asyncio.Event] = {}

        # Counter for insertion order (FIFO within same priority)
        self._insertion_order_counter = 0

        # Thread tracking indexes
        self._thread_index: Dict[str, Set[str]] = {}
        self._thread_metadata: Dict[str, ThreadMetadata] = {}
        
        # Set of thread IDs that have pending messages
        self._active_threads: Set[str] = set()

    # ============================================================================
    # Public API: Message Queue Operations
    # ============================================================================

    async def enqueue(
        self,
        user_message: str,
        thread_id: str,
        priority: Priority = Priority.NORMAL,
    ) -> QueuedMessage:
        """
        Add a message to the queue.

        Args:
            user_message: The user's message text
            thread_id: Thread ID to group related messages (always required)
            priority: Message priority level

        Returns:
            The created QueuedMessage object
        """
        async with self._lock:
            message = operations.create_message(user_message, thread_id, priority)
            self._messages[message.id] = message
            threads.initialize_or_update_thread_metadata(
                thread_id, message, self._thread_index, self._thread_metadata
            )
            operations.ensure_thread_resources(
                thread_id, self._thread_queues, self._thread_events
            )
            self._insertion_order_counter = await operations.add_message_to_queue(
                thread_id, priority, message.id, self._thread_queues, self._insertion_order_counter
            )
            self._active_threads.add(thread_id)
            operations.log_message_enqueued(message, thread_id, self._thread_queues)
            operations.signal_thread_message_available(thread_id, self._thread_events)
            return message

    async def dequeue(self, thread_id: str) -> Optional[QueuedMessage]:
        """
        Remove and return the next message from a specific thread's queue.

        Args:
            thread_id: The thread ID to dequeue from

        Returns:
            The next QueuedMessage or None if thread queue is empty
        """
        async with self._lock:
            if thread_id not in self._thread_queues:
                return None
            thread_queue = self._thread_queues[thread_id]

        try:
            _, _, message_id = thread_queue.get_nowait()
            return await operations.process_dequeued_message(
                thread_id,
                thread_queue,
                message_id,
                self._messages,
                self._active_threads,
                self._lock,
                self._update_thread_state_counts,
            )
        except asyncio.QueueEmpty:
            async with self._lock:
                self._active_threads.discard(thread_id)
            return None

    async def update_state(
        self, message_id: str, new_state: MessageState, error: Optional[str] = None
    ) -> bool:
        """
        Update the state of a message.

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

            if not state.validate_state_transition(message.state, new_state):
                logger.warning(
                    f"Invalid state transition: id={message_id}, "
                    f"from={message.state}, to={new_state}"
                )
                return False

            return state.apply_state_change(
                message, new_state, error, message_id, self._update_thread_state_counts
            )

    async def get_message(self, message_id: str) -> Optional[QueuedMessage]:
        """
        Get a message by ID.

        Args:
            message_id: The message ID

        Returns:
            The QueuedMessage or None if not found
        """
        async with self._lock:
            return self._messages.get(message_id)

    async def cancel_message(self, message_id: str) -> CancelResult:
        """
        Cancel a message if it's still queued.

        Args:
            message_id: The message ID

        Returns:
            CancelResult with success status and optional error message
        """
        async with self._lock:
            message = self._messages.get(message_id)
            if not message:
                return CancelResult(False, "Message not found")

            if message.state != MessageState.QUEUED:
                return CancelResult(False, f"Cannot cancel message in state: {message.state}")

            old_state = message.state
            message.state = MessageState.CANCELLED
            message.completed_at = datetime.utcnow()
            self._update_thread_state_counts(message, old_state, MessageState.CANCELLED)
            logger.info(f"Message cancelled: id={message_id}")
            return CancelResult(True, None)

    async def set_result(self, message_id: str, result: str) -> bool:
        """
        Set the result for a completed message.

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
        Add a streaming chunk to a message.

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
        Get the queue position of a message.

        Args:
            message_id: The message ID

        Returns:
            Queue position (0-indexed) or None if not in queue
        """
        async with self._lock:
            message = self._messages.get(message_id)
            if not message or message.state != MessageState.QUEUED:
                return None

            message_priority_value = summary.calculate_message_priority_value(message.priority)
            return summary.count_higher_priority_messages(
                message_id, message_priority_value, message.created_at, self._messages
            )

    async def get_queue_summary(self) -> QueueSummaryResponse:
        """
        Get a summary of the queue state.

        Returns:
            QueueSummaryResponse object
        """
        async with self._lock:
            state_counts = summary.count_messages_by_state(self._messages)
            queued_messages = summary.build_queued_message_list(self._messages)
            current_processing = summary.build_current_processing_message(self._messages)

            return QueueSummaryResponse(
                total_queued=state_counts[MessageState.QUEUED],
                total_processing=state_counts[MessageState.PROCESSING],
                total_completed=state_counts[MessageState.COMPLETED],
                total_failed=state_counts[MessageState.FAILED],
                total_cancelled=state_counts[MessageState.CANCELLED],
                queued_messages=queued_messages,
                current_processing=current_processing,
            )

    # ============================================================================
    # Public API: Thread Operations
    # ============================================================================

    async def wait_for_messages(self, thread_id: Optional[str] = None) -> None:
        """
        Wait until a new message is added to a thread's queue.
        
        Args:
            thread_id: Optional thread ID to wait for. If None, waits for any thread.
        """
        if thread_id:
            await threads.wait_for_specific_thread(
                thread_id, self._thread_events, self._lock
            )
        else:
            await threads.wait_for_any_thread(self._thread_events, self._lock)

    def has_messages(self, thread_id: Optional[str] = None) -> bool:
        """
        Check if there are messages in the queue.
        
        Args:
            thread_id: Optional thread ID to check. If None, checks all threads.
            
        Returns:
            True if there are messages, False otherwise
        """
        if thread_id:
            return thread_id in self._thread_queues and not self._thread_queues[thread_id].empty()
        else:
            return len(self._active_threads) > 0
    
    def get_active_threads(self) -> Set[str]:
        """
        Get all thread IDs that have pending messages.
        
        Returns:
            Set of thread IDs with pending messages
        """
        return self._active_threads.copy()
    
    async def get_next_thread_with_messages(self) -> Optional[str]:
        """
        Get the next thread ID that has pending messages.
        
        Returns:
            Thread ID with pending messages, or None if no threads have messages
        """
        async with self._lock:
            if not self._active_threads:
                return None
            return next(iter(self._active_threads))

    async def get_thread_messages(self, thread_id: str) -> List[QueuedMessage]:
        """
        Return all messages for a given thread sorted chronologically.

        Args:
            thread_id: The thread ID

        Returns:
            List of QueuedMessage objects sorted by creation time
        """
        async with self._lock:
            message_ids = self._thread_index.get(thread_id)
            if not message_ids:
                return []

            messages = [
                self._messages[msg_id]
                for msg_id in message_ids
                if msg_id in self._messages
            ]

            messages.sort(key=lambda msg: msg.created_at)
            return messages

    async def get_thread_metadata(self, thread_id: str) -> Optional[ThreadMetadata]:
        """
        Return metadata for a specific thread.

        Args:
            thread_id: The thread ID

        Returns:
            ThreadMetadata or None if thread doesn't exist
        """
        async with self._lock:
            metadata = self._thread_metadata.get(thread_id)
            if not metadata:
                return None
            return metadata.model_copy(deep=True)

    async def list_threads(self) -> List[ThreadSummary]:
        """
        Return summary information for all threads sorted by last activity.

        Returns:
            List of ThreadSummary objects sorted by last activity (most recent first)
        """
        async with self._lock:
            summaries: List[ThreadSummary] = []

            for thread_id, metadata in self._thread_metadata.items():
                message_ids = self._thread_index.get(thread_id, set())
                messages = [
                    self._messages[msg_id]
                    for msg_id in message_ids
                    if msg_id in self._messages
                ]

                last_message_preview = threads.extract_last_message_preview(messages)
                summaries.append(
                    ThreadSummary(
                        thread_id=thread_id,
                        message_count=metadata.message_count,
                        created_at=metadata.created_at,
                        last_activity=metadata.last_activity,
                        last_message_preview=last_message_preview,
                    )
                )

            summaries.sort(key=lambda summary: summary.last_activity, reverse=True)
            return summaries

    # ============================================================================
    # Internal Helpers: Thread State Management
    # ============================================================================

    def _update_thread_state_counts(
        self, message: QueuedMessage, old_state: MessageState, new_state: MessageState
    ) -> None:
        """Update thread metadata when a message state changes."""
        threads.update_thread_state_counts(
            message, old_state, new_state, self._thread_metadata
        )

