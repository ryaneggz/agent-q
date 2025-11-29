"""Thread management helpers for thread metadata and operations."""

import asyncio
from datetime import datetime
from typing import Dict, Set, List, Optional

from shinzo.models import QueuedMessage, MessageState, ThreadMetadata, ThreadSummary


def initialize_or_update_thread_metadata(
    thread_id: str,
    message: QueuedMessage,
    thread_index: Dict[str, Set[str]],
    thread_metadata: Dict[str, ThreadMetadata],
) -> None:
    """Initialize and update thread metadata for a message."""
    if thread_id not in thread_index:
        thread_index[thread_id] = set()
        thread_metadata[thread_id] = ThreadMetadata(
            thread_id=thread_id,
            message_count=0,
            created_at=message.created_at,
            last_activity=message.created_at,
            states={state: 0 for state in MessageState},
        )

    thread_index[thread_id].add(message.id)

    metadata = thread_metadata[thread_id]
    metadata.message_count += 1
    metadata.last_activity = message.created_at
    metadata.states[message.state] = metadata.states.get(message.state, 0) + 1


def update_thread_state_counts(
    message: QueuedMessage,
    old_state: MessageState,
    new_state: MessageState,
    thread_metadata: Dict[str, ThreadMetadata],
) -> None:
    """Update thread metadata when a message state changes."""
    if not message.thread_id:
        return

    metadata = thread_metadata.get(message.thread_id)
    if not metadata:
        return

    metadata.states[old_state] = max(
        0, metadata.states.get(old_state, 0) - 1
    )
    metadata.states[new_state] = metadata.states.get(new_state, 0) + 1
    metadata.last_activity = datetime.utcnow()


async def ensure_thread_event(
    thread_id: str,
    thread_events: Dict[str, asyncio.Event],
    lock: asyncio.Lock,
) -> None:
    """Ensure a thread event exists, creating it if necessary."""
    if thread_id not in thread_events:
        async with lock:
            if thread_id not in thread_events:
                thread_events[thread_id] = asyncio.Event()


async def wait_for_specific_thread(
    thread_id: str,
    thread_events: Dict[str, asyncio.Event],
    lock: asyncio.Lock,
) -> None:
    """Wait for a specific thread to have messages."""
    await ensure_thread_event(thread_id, thread_events, lock)
    await thread_events[thread_id].wait()
    thread_events[thread_id].clear()


async def wait_for_any_thread(
    thread_events: Dict[str, asyncio.Event],
    lock: asyncio.Lock,
) -> None:
    """Wait for any thread to have messages."""
    async with lock:
        if not thread_events:
            await asyncio.sleep(0.1)
            return
        events = list(thread_events.values())
    
    if events:
        done, pending = await asyncio.wait(
            [asyncio.create_task(event.wait()) for event in events],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()


def extract_last_message_preview(messages: List[QueuedMessage]) -> Optional[str]:
    """Extract preview text from the most recent message."""
    if not messages:
        return None
    
    last_message = max(messages, key=lambda msg: msg.created_at)
    preview_text = last_message.user_message
    if len(preview_text) > 100:
        preview_text = preview_text[:97] + "..."
    return preview_text

