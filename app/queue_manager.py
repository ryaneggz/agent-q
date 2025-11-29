import asyncio
from datetime import datetime
from typing import Optional, Dict, Set, List

from app.models import (
    QueuedMessage,
    MessageState,
    Priority,
    PRIORITY_MAP,
    QueueSummaryResponse,
    ThreadMetadata,
    ThreadSummary,
)
from app.utils import get_logger


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
        self._counter = 0

        # Thread tracking indexes
        self._thread_index: Dict[str, Set[str]] = {}
        self._thread_metadata: Dict[str, ThreadMetadata] = {}
        
        # Set of thread IDs that have pending messages
        self._active_threads: Set[str] = set()

    async def enqueue(
        self,
        user_message: str,
        thread_id: str,
        priority: Priority = Priority.NORMAL,
    ) -> QueuedMessage:
        """
        Add a message to the queue

        Args:
            user_message: The user's message text
            thread_id: Thread ID to group related messages (always required)
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
                thread_id=thread_id,
            )

            # Store message metadata
            self._messages[message.id] = message

            # Track thread association (including None for backward compatibility)
            self._track_thread_message(thread_id, message)

            # Ensure thread has a queue and event
            if thread_id not in self._thread_queues:
                self._thread_queues[thread_id] = asyncio.PriorityQueue()
                self._thread_events[thread_id] = asyncio.Event()

            # Add to thread-specific priority queue
            # Priority queue uses (priority, counter) tuple for ordering
            # Lower priority number = higher priority
            # Counter ensures FIFO within same priority
            priority_value = PRIORITY_MAP[priority]
            await self._thread_queues[thread_id].put((priority_value, self._counter, message.id))
            self._counter += 1

            # Mark thread as active
            self._active_threads.add(thread_id)

            queue_size = self._thread_queues[thread_id].qsize()
            logger.info(
                f"Message enqueued: id={message.id}, thread_id={thread_id}, "
                f"priority={priority}, thread_queue_size={queue_size}"
            )

            # Signal that a new message is available for this thread
            self._thread_events[thread_id].set()

            return message

    async def dequeue(self, thread_id: str) -> Optional[QueuedMessage]:
        """
        Remove and return the next message from a specific thread's queue

        Args:
            thread_id: The thread ID to dequeue from

        Returns:
            The next QueuedMessage or None if thread queue is empty
        """
        async with self._lock:
            # Check if thread has a queue
            if thread_id not in self._thread_queues:
                return None

            thread_queue = self._thread_queues[thread_id]

        try:
            # Get next message (non-blocking)
            _, _, message_id = thread_queue.get_nowait()

            async with self._lock:
                message = self._messages.get(message_id)

                if message and message.state == MessageState.QUEUED:
                    # Update state to processing
                    message.state = MessageState.PROCESSING
                    message.started_at = datetime.utcnow()
                    self._update_thread_state_counts(
                        message, MessageState.QUEUED, MessageState.PROCESSING
                    )

                    # Remove thread from active if queue is now empty
                    if thread_queue.empty():
                        self._active_threads.discard(thread_id)

                    logger.info(f"Message dequeued: id={message.id}, thread_id={thread_id}")
                    return message
                elif message and message.state == MessageState.CANCELLED:
                    # Message was cancelled, skip it
                    logger.info(f"Skipping cancelled message: id={message.id}")
                    
                    # Check if queue is now empty
                    if thread_queue.empty():
                        self._active_threads.discard(thread_id)
                    
                    return None
                else:
                    logger.warning(f"Message not found or invalid state: id={message_id}")
                    return None

        except asyncio.QueueEmpty:
            async with self._lock:
                self._active_threads.discard(thread_id)
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

            # Update thread metadata if needed
            self._update_thread_state_counts(message, old_state, new_state)

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
            old_state = message.state
            message.state = MessageState.CANCELLED
            message.completed_at = datetime.utcnow()
            self._update_thread_state_counts(
                message, old_state, MessageState.CANCELLED
            )

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

    async def wait_for_messages(self, thread_id: Optional[str] = None):
        """
        Wait until a new message is added to a thread's queue
        
        Args:
            thread_id: Optional thread ID to wait for. If None, waits for any thread.
        """
        if thread_id:
            # Wait for specific thread
            if thread_id not in self._thread_events:
                async with self._lock:
                    if thread_id not in self._thread_events:
                        self._thread_events[thread_id] = asyncio.Event()
            
            await self._thread_events[thread_id].wait()
            self._thread_events[thread_id].clear()
        else:
            # Wait for any thread to have messages
            # Create a task for each thread event
            async with self._lock:
                if not self._thread_events:
                    # No threads yet, wait briefly
                    await asyncio.sleep(0.1)
                    return
                
                events = list(self._thread_events.values())
            
            if events:
                # Wait for any event to be set
                done, pending = await asyncio.wait(
                    [asyncio.create_task(event.wait()) for event in events],
                    return_when=asyncio.FIRST_COMPLETED
                )
                # Cancel pending tasks
                for task in pending:
                    task.cancel()

    def has_messages(self, thread_id: Optional[str] = None) -> bool:
        """
        Check if there are messages in the queue
        
        Args:
            thread_id: Optional thread ID to check. If None, checks all threads.
            
        Returns:
            True if there are messages, False otherwise
        """
        if thread_id:
            # Check specific thread
            return thread_id in self._thread_queues and not self._thread_queues[thread_id].empty()
        else:
            # Check any thread
            return len(self._active_threads) > 0
    
    def get_active_threads(self) -> Set[str]:
        """
        Get all thread IDs that have pending messages
        
        Returns:
            Set of thread IDs with pending messages
        """
        return self._active_threads.copy()
    
    async def get_next_thread_with_messages(self) -> Optional[str]:
        """
        Get the next thread ID that has pending messages
        
        Returns:
            Thread ID with pending messages, or None if no threads have messages
        """
        async with self._lock:
            if not self._active_threads:
                return None
            # Return any active thread (could be enhanced with priority logic)
            return next(iter(self._active_threads))

    def _track_thread_message(self, thread_id: str, message: QueuedMessage) -> None:
        """Initialize and update thread metadata for a message"""
        if thread_id not in self._thread_index:
            self._thread_index[thread_id] = set()
            self._thread_metadata[thread_id] = ThreadMetadata(
                thread_id=thread_id,
                message_count=0,
                created_at=message.created_at,
                last_activity=message.created_at,
                states={state: 0 for state in MessageState},
            )

        self._thread_index[thread_id].add(message.id)

        metadata = self._thread_metadata[thread_id]
        metadata.message_count += 1
        metadata.last_activity = message.created_at
        metadata.states[message.state] = metadata.states.get(message.state, 0) + 1

    def _update_thread_state_counts(
        self, message: QueuedMessage, old_state: MessageState, new_state: MessageState
    ) -> None:
        """Update thread metadata when a message state changes"""
        if not message.thread_id:
            return

        metadata = self._thread_metadata.get(message.thread_id)
        if not metadata:
            return

        metadata.states[old_state] = max(
            0, metadata.states.get(old_state, 0) - 1
        )
        metadata.states[new_state] = metadata.states.get(new_state, 0) + 1
        metadata.last_activity = datetime.utcnow()

    async def get_thread_messages(self, thread_id: str) -> List[QueuedMessage]:
        """Return all messages for a given thread sorted chronologically"""
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
        """Return metadata for a specific thread"""
        async with self._lock:
            metadata = self._thread_metadata.get(thread_id)
            if not metadata:
                return None

            return metadata.model_copy(deep=True)

    async def list_threads(self) -> List[ThreadSummary]:
        """Return summary information for all threads sorted by last activity"""
        async with self._lock:
            summaries: List[ThreadSummary] = []

            for thread_id, metadata in self._thread_metadata.items():
                message_ids = self._thread_index.get(thread_id, set())
                messages = [
                    self._messages[msg_id]
                    for msg_id in message_ids
                    if msg_id in self._messages
                ]

                last_message_preview = None
                if messages:
                    last_message = max(messages, key=lambda msg: msg.created_at)
                    preview_text = last_message.user_message
                    if len(preview_text) > 100:
                        preview_text = preview_text[:97] + "..."
                    last_message_preview = preview_text

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
